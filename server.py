#!/usr/bin/env python3
"""
MCP Server for China Drug Clinical Trial Registration Platform
(药物临床试验登记与信息公示平台 - chinadrugtrials.org.cn)

Operated by NMPA Center for Drug Evaluation (CDE).
Uses Playwright for browser automation due to JavaScript anti-bot protection.
"""

from contextlib import asynccontextmanager
from typing import Optional, Dict, Any
from enum import Enum
import asyncio
import json
import re
import html as html_lib

from pydantic import BaseModel, Field, ConfigDict
from mcp.server.fastmcp import FastMCP


# --- Constants ---

BASE_URL = "https://www.chinadrugtrials.org.cn"
SEARCH_LIST_URL = f"{BASE_URL}/clinicaltrials.searchlist.dhtml"
STATISTICS_URL = f"{BASE_URL}/clinicaltrials.tongji.dhtml"


# --- Enums ---

class DrugType(str, Enum):
    ALL = ""
    TCM = "中药/天然药物"
    CHEMICAL = "化学药物"
    BIOLOGICAL = "生物制品"


class TrialStatus(str, Enum):
    ALL = ""
    ONGOING = "进行中"
    NOT_RECRUITING = "尚未招募"
    RECRUITING = "招募中"
    RECRUITMENT_COMPLETE = "招募完成"
    COMPLETED = "已完成"
    VOLUNTARILY_SUSPENDED = "主动暂停"
    VOLUNTARILY_TERMINATED = "主动终止"
    IEC_SUSPENDED = "IEC/IRB暂停"
    IEC_TERMINATED = "IEC/IRB终止"
    MANDATORY_SUSPENDED = "责令暂停"
    MANDATORY_TERMINATED = "责令终止"


class ResponseFormat(str, Enum):
    MARKDOWN = "markdown"
    JSON = "json"


# --- Pydantic Input Models ---

class SearchTrialsInput(BaseModel):
    """Input for searching clinical trials on the China Drug Trials platform."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    drugs_name: Optional[str] = Field(default=None, description="Drug name to search (e.g., 'PD-1', '阿托伐他汀钙片')")
    reg_no: Optional[str] = Field(default=None, description="Registration number (e.g., 'CTR20261395'). Exact or partial match.")
    indication: Optional[str] = Field(default=None, description="Indication/disease area (e.g., '肺癌', '糖尿病')")
    case_no: Optional[str] = Field(default=None, description="Protocol/trial case number")
    drugs_type: Optional[DrugType] = Field(default=DrugType.ALL, description="Drug type: empty=all, '中药/天然药物', '化学药物', '生物制品'")
    appliers: Optional[str] = Field(default=None, description="Sponsor/applicant company name (e.g., '恒瑞')")
    researchers: Optional[str] = Field(default=None, description="Principal investigator name")
    agencies: Optional[str] = Field(default=None, description="Clinical trial site/institution name")
    state: Optional[TrialStatus] = Field(default=TrialStatus.ALL, description="Trial status filter")
    communities: Optional[str] = Field(default=None, description="Ethics committee / IRB name")
    page: int = Field(default=1, description="Page number (1-based)", ge=1, le=100)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format: 'markdown' or 'json'")


class GetTrialDetailInput(BaseModel):
    """Input for getting detailed trial information."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    reg_no: str = Field(..., description="Trial registration number (e.g., 'CTR20261395')", min_length=1)
    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format: 'markdown' or 'json'")


class GetStatisticsInput(BaseModel):
    """Input for getting trial statistics."""
    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    response_format: ResponseFormat = Field(default=ResponseFormat.MARKDOWN, description="Output format: 'markdown' or 'json'")


# --- Browser Manager ---

class BrowserManager:
    """Manages a persistent Playwright browser instance for the session."""

    def __init__(self):
        self._browser = None
        self._context = None
        self._playwright = None
        self._lock = asyncio.Lock()

    async def get_page(self):
        """Get a new browser page, reusing the browser instance."""
        async with self._lock:
            if self._browser is None:
                try:
                    from playwright.async_api import async_playwright
                except ImportError:
                    raise RuntimeError(
                        "Playwright not installed. Run: pip install playwright && playwright install chromium"
                    )
                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(headless=True)
                self._context = await self._browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                    viewport={"width": 1920, "height": 1080},
                )
            return await self._context.new_page()

    async def close_page(self, page):
        """Close a single page."""
        await page.close()

    async def cleanup(self):
        """Clean up all browser resources."""
        async with self._lock:
            if self._browser:
                await self._browser.close()
                await self._playwright.stop()
                self._browser = None
                self._context = None
                self._playwright = None


browser_mgr = BrowserManager()


# --- Helper Functions ---

def _clean_text(text: str) -> str:
    """Clean HTML-encoded text and normalize whitespace."""
    text = html_lib.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _handle_error(e: Exception) -> str:
    """Format error messages for users."""
    err_type = type(e).__name__
    if "Playwright" in err_type or "playwright" in err_type:
        return "Error: Playwright browser engine not available. Install with: pip install playwright && playwright install chromium"
    if "Timeout" in err_type:
        return "Error: Request timed out. The chinadrugtrials.org.cn server may be slow. Please try again."
    if "net" in err_type.lower() or "connection" in str(e).lower():
        return "Error: Network error connecting to chinadrugtrials.org.cn. Check your internet connection."
    return f"Error: {err_type}: {str(e)[:200]}"


def _parse_search_results(html: str) -> Dict[str, Any]:
    """Parse the search results table from HTML."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")

    # Extract pagination info
    pagination = {}
    page_elem = soup.find(string=re.compile(r"当前第.*页"))
    if page_elem:
        m = re.search(r"当前第\s*(\d+)\s*页.*共\s*(\d+)\s*页.*共\s*(\d+)\s*条", page_elem)
        if m:
            pagination = {
                "current_page": int(m.group(1)),
                "total_pages": int(m.group(2)),
                "total_records": int(m.group(3)),
            }

    trials = []
    table = soup.find("table", class_="table") or soup.find("table")
    if not table:
        return {"trials": [], "pagination": pagination}

    tbody = table.find("tbody") or table
    for row in tbody.find_all("tr")[1:]:  # Skip header
        cells = row.find_all("td")
        if len(cells) < 6:
            continue

        def _cell_text(idx):
            elem = cells[idx].find("a")
            return _clean_text(elem.get_text()) if elem else _clean_text(cells[idx].get_text())

        trials.append({
            "reg_no": _cell_text(1),
            "status": _cell_text(2),
            "drug_name": _cell_text(3),
            "indication": _cell_text(4),
            "title": _cell_text(5),
        })

    return {"trials": trials, "pagination": pagination}


def _parse_detail(html: str) -> Dict[str, Any]:
    """Parse the trial detail page HTML into a flat key-value dict."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    result = {}

    field_map = {
        "登记号": "reg_no", "试验状态": "status",
        "申请人联系人": "sponsor_contact",
        "首次公示信息日期": "first_publication_date",
        "最新公示信息日期": "latest_publication_date",
        "申请人名称": "sponsor_name",
        "申请人联系人邮政编码": "sponsor_postal_code",
        "申请人联系人电话": "sponsor_phone",
        "申请人联系人邮箱": "sponsor_email",
        "试验分类": "trial_category",
        "试验分期": "trial_phase",
        "试验专业": "trial_specialty",
        "药物名称": "drug_name",
        "药物类型": "drug_type",
        "适应症": "indication",
        "试验通俗题目": "trial_title",
        "试验科学题目": "trial_scientific_title",
        "试验方案编号": "protocol_number",
        "目标入组人数": "target_enrollment",
        "实际入组人数": "actual_enrollment",
        "第一例受试者签署知情同意书日期": "first_consent_date",
        "国内试验日期": "domestic_trial_date",
        "国内试验登记号": "domestic_reg_no",
    }

    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = row.find_all(["th", "td"])
            i = 0
            while i < len(cells):
                key_text = _clean_text(cells[i].get_text())
                if key_text and i + 1 < len(cells):
                    value = _clean_text(cells[i + 1].get_text())
                    key_en = field_map.get(key_text, key_text)
                    result[key_en] = value
                    i += 2
                else:
                    i += 1

    return result


def _format_search_markdown(data: Dict[str, Any]) -> str:
    """Format search results as markdown."""
    trials = data.get("trials", [])
    pag = data.get("pagination", {})
    total = pag.get("total_records", len(trials))
    cur = pag.get("current_page", 1)
    pages = pag.get("total_pages", 1)

    lines = ["# China Drug Clinical Trial Search Results", ""]
    lines.append(f"**{total}** trials found | Page {cur}/{pages} | Showing {len(trials)} results\n")

    if not trials:
        return lines[0] + "\n\nNo trials found."

    for i, t in enumerate(trials, 1):
        lines.append(f"**{i}. {t['reg_no']}** — {t['status']}")
        lines.append(f"  - Drug: {t['drug_name']}")
        lines.append(f"  - Indication: {t['indication']}")
        lines.append(f"  - Title: {t['title']}")
        lines.append("")

    if pages > 1:
        lines.append(f"---\nUse `page` param to navigate (1–{pages})")

    return "\n".join(lines)


def _format_detail_markdown(detail: Dict[str, Any], reg_no: str) -> str:
    """Format trial detail as markdown."""
    lines = [f"# Trial Detail: {reg_no}", ""]

    if not detail:
        return lines[0] + "\n\nNo detail found. The trial may have been removed."

    display_order = [
        ("reg_no", "Registration No."), ("status", "Status"),
        ("sponsor_name", "Sponsor"), ("sponsor_contact", "Contact"),
        ("sponsor_phone", "Phone"), ("sponsor_email", "Email"),
        ("first_publication_date", "First Published"),
        ("trial_category", "Category"), ("trial_phase", "Phase"),
        ("drug_name", "Drug Name"), ("drug_type", "Drug Type"),
        ("indication", "Indication"), ("trial_title", "Trial Title"),
        ("trial_scientific_title", "Scientific Title"),
        ("protocol_number", "Protocol No."),
        ("target_enrollment", "Target Enrollment"),
        ("actual_enrollment", "Actual Enrollment"),
        ("first_consent_date", "First Consent Date"),
    ]

    shown = set()
    for key, label in display_order:
        if key in detail and detail[key]:
            lines.append(f"**{label}**: {detail[key]}")
            shown.add(key)

    for key, value in detail.items():
        if key not in shown and value:
            lines.append(f"**{key}**: {value}")

    return "\n".join(lines)


def _format_stats_markdown(soup) -> str:
    """Format statistics page content as markdown."""
    from bs4 import BeautifulSoup
    lines = ["# China Drug Clinical Trial Statistics", ""]
    main = soup.find("main") or soup.find("div", class_="main") or soup.body

    if main:
        for table in main.find_all("table"):
            rows = table.find_all("tr")
            headers = []
            for row in rows:
                cells = row.find_all(["th", "td"])
                row_data = [_clean_text(c.get_text()) for c in cells]
                if not row_data:
                    continue
                if cells[0].name == "th" and not headers:
                    headers = row_data
                else:
                    if headers:
                        entry = " | ".join(f"{h}: {v}" for h, v in zip(headers, row_data))
                    else:
                        entry = " | ".join(row_data)
                    lines.append(f"- {entry}")
            lines.append("")

    return "\n".join(lines)


# --- Tool Implementations ---

async def _search_trials(params: SearchTrialsInput) -> str:
    """Core search logic shared by the tool."""
    page = None
    try:
        query = {
            "reg_no": params.reg_no or "",
            "indication": params.indication or "",
            "case_no": params.case_no or "",
            "drugs_name": params.drugs_name or "",
            "drugs_type": params.drugs_type.value if params.drugs_type else "",
            "appliers": params.appliers or "",
            "communities": params.communities or "",
            "researchers": params.researchers or "",
            "agencies": params.agencies or "",
            "state": params.state.value if params.state else "",
        }

        page = await browser_mgr.get_page()
        param_str = "&".join(f"{k}={v}" for k, v in query.items())
        await page.goto(f"{SEARCH_LIST_URL}?{param_str}", wait_until="domcontentloaded", timeout=60000)

        try:
            await page.wait_for_selector("table.table, table", timeout=30000)
        except Exception:
            pass

        # Pagination
        if params.page > 1:
            page_input = await page.query_selector("input.page-num, input[class*='page']")
            if page_input:
                await page_input.fill(str(params.page))
                go_btn = await page.query_selector("button:has-text('跳转')")
                if go_btn:
                    await go_btn.click()
                    await page.wait_for_timeout(2000)

        content = await page.content()
        data = _parse_search_results(content)

        return json.dumps(data, ensure_ascii=False, indent=2) if params.response_format == ResponseFormat.JSON else _format_search_markdown(data)

    except Exception as e:
        return _handle_error(e)
    finally:
        if page:
            try:
                await browser_mgr.close_page(page)
            except Exception:
                pass


async def _get_trial_detail(params: GetTrialDetailInput) -> str:
    """Core detail logic shared by the tool."""
    page = None
    try:
        page = await browser_mgr.get_page()

        # Navigate to search with registration number
        search_url = f"{SEARCH_LIST_URL}?reg_no={params.reg_no}&indication=&case_no=&drugs_name=&drugs_type=&appliers=&communities=&researchers=&agencies=&state="
        await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)

        try:
            await page.wait_for_selector("table.table, table", timeout=30000)
        except Exception:
            pass

        content = await page.content()
        if params.reg_no not in content:
            msg = {"error": f"Trial {params.reg_no} not found"}
            return json.dumps(msg, ensure_ascii=False) if params.response_format == ResponseFormat.JSON else f"# Trial Not Found\n\n`{params.reg_no}` was not found."

        # Click registration number link to open detail tab
        reg_link = await page.query_selector(f"a:has-text('{params.reg_no}')")
        if reg_link:
            async with page.context.expect_page() as new_page_info:
                await reg_link.click()
            detail_page = new_page_info.value

            try:
                await detail_page.wait_for_selector("table", timeout=30000)
            except Exception:
                await detail_page.wait_for_timeout(3000)

            detail_content = await detail_page.content()
            await detail_page.close()
        else:
            detail_content = content

        detail = _parse_detail(detail_content)

        return json.dumps(detail, ensure_ascii=False, indent=2) if params.response_format == ResponseFormat.JSON else _format_detail_markdown(detail, params.reg_no)

    except Exception as e:
        return _handle_error(e)
    finally:
        if page:
            try:
                await browser_mgr.close_page(page)
            except Exception:
                pass


async def _get_statistics(params: GetStatisticsInput) -> str:
    """Core statistics logic shared by the tool."""
    page = None
    try:
        page = await browser_mgr.get_page()
        await page.goto(STATISTICS_URL, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(3000)

        content = await page.content()
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(content, "lxml")

        if params.response_format == ResponseFormat.JSON:
            # Extract structured table data
            main = soup.find("main") or soup.body
            stats = {}
            if main:
                for table in main.find_all("table"):
                    rows = table.find_all("tr")
                    headers = []
                    table_data = []
                    for row in rows:
                        cells = row.find_all(["th", "td"])
                        row_vals = [_clean_text(c.get_text()) for c in cells]
                        if cells[0].name == "th" and not headers:
                            headers = row_vals
                        else:
                            table_data.append(dict(zip(headers, row_vals)) if headers else row_vals)
                    if table_data:
                        key = headers[0] if headers else "table"
                        stats[key] = table_data
            if not stats:
                stats = {"raw_text": _clean_text(soup.get_text())[:2000]}
            return json.dumps(stats, ensure_ascii=False, indent=2)
        else:
            return _format_stats_markdown(soup)

    except Exception as e:
        return _handle_error(e)
    finally:
        if page:
            try:
                await browser_mgr.close_page(page)
            except Exception:
                pass


# --- Lifespan ---

@asynccontextmanager
async def app_lifespan(app):
    """Manage browser lifecycle across the MCP server session."""
    yield {}
    try:
        await browser_mgr.cleanup()
    except Exception:
        pass


# --- MCP Server with Tools ---

mcp = FastMCP("chinadrugtrials_mcp", lifespan=app_lifespan)


@mcp.tool(
    name="chinadrugtrials_search_trials",
    annotations={
        "title": "Search China Drug Clinical Trials",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def chinadrugtrials_search_trials(params: SearchTrialsInput) -> str:
    """Search clinical trials on China's Drug Clinical Trial Registration Platform (chinadrugtrials.org.cn).

    Operated by NMPA/CDE, this is China's primary public registry for drug clinical trials,
    analogous to ClinicalTrials.gov in the US. Supports searching by drug name, registration
    number, indication, sponsor, PI, trial site, drug type, and trial status.

    Args:
        params (SearchTrialsInput):
            - drugs_name (str): Drug name (e.g., 'PD-1', '阿托伐他汀钙片')
            - reg_no (str): Registration number (e.g., 'CTR20261395')
            - indication (str): Disease/indication (e.g., '肺癌')
            - drugs_type (DrugType): '中药/天然药物', '化学药物', '生物制品', or empty for all
            - appliers (str): Sponsor company name
            - researchers (str): Principal investigator
            - agencies (str): Clinical trial site
            - state (TrialStatus): '进行中', '招募中', '已完成', etc.
            - page (int): Page number (default 1, 20 results/page)
            - response_format: 'markdown' or 'json'

    Returns:
        str: Paginated trial list with reg_no, status, drug_name, indication, title.
    """
    return await _search_trials(params)


@mcp.tool(
    name="chinadrugtrials_get_trial_detail",
    annotations={
        "title": "Get Trial Detail from China Drug Trials",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def chinadrugtrials_get_trial_detail(params: GetTrialDetailInput) -> str:
    """Get detailed information for a specific clinical trial from China's Drug Clinical Trial Registration Platform.

    Provide a registration number (e.g., CTR20261395) to retrieve full trial details including
    sponsor info, trial phase, drug details, enrollment targets, and more.

    Args:
        params (GetTrialDetailInput):
            - reg_no (str): Trial registration number (e.g., 'CTR20261395')
            - response_format: 'markdown' or 'json'

    Returns:
        str: Full trial details (reg_no, status, sponsor, drug, indication, phase, enrollment, etc.)
    """
    return await _get_trial_detail(params)


@mcp.tool(
    name="chinadrugtrials_get_statistics",
    annotations={
        "title": "Get China Drug Trial Statistics",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def chinadrugtrials_get_statistics(params: GetStatisticsInput) -> str:
    """Get clinical trial registration statistics from China's Drug Clinical Trial Registration Platform.

    Displays aggregate statistics about registered trials including counts by drug type,
    trial phase, and other dimensions.

    Args:
        params (GetStatisticsInput):
            - response_format: 'markdown' or 'json'

    Returns:
        str: Trial statistics (registration counts, drug type distribution, phase distribution, etc.)
    """
    return await _get_statistics(params)


if __name__ == "__main__":
    mcp.run()
