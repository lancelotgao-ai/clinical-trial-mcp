"""HTML parsing helpers and formatting utilities."""

import re
import html as html_lib
from typing import Dict, Any

from bs4 import BeautifulSoup

from .constants import BASE_URL


def _clean_text(text: str) -> str:
    """Clean HTML-encoded text and normalize whitespace."""
    text = html_lib.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _handle_error(e: Exception) -> str:
    """Format error messages for users with recovery hints."""
    from .constants import RECOVERY_HINTS

    err_type = type(e).__name__
    if "Playwright" in err_type or "playwright" in str(e).lower():
        return f"Error: {RECOVERY_HINTS['playwright']}"
    if "Timeout" in err_type:
        return f"Error: {RECOVERY_HINTS['timeout']}"
    if "net" in err_type.lower() or "connection" in str(e).lower():
        return f"Error: {RECOVERY_HINTS['connection']}"
    return f"Error: {err_type}: {str(e)[:200]}"


# --- Search Results ---

def parse_search_results(html: str) -> Dict[str, Any]:
    """Parse the search results table from HTML."""
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


def format_search_markdown(data: Dict[str, Any]) -> str:
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


# --- Trial Detail ---

FIELD_MAP = {
    "登记号": "reg_no",
    "试验状态": "status",
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


def parse_detail(html: str) -> Dict[str, Any]:
    """Parse the trial detail page HTML into a flat key-value dict."""
    soup = BeautifulSoup(html, "lxml")
    result = {}

    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = row.find_all(["th", "td"])
            i = 0
            while i < len(cells):
                key_text = _clean_text(cells[i].get_text())
                if key_text and i + 1 < len(cells):
                    value = _clean_text(cells[i + 1].get_text())
                    key_en = FIELD_MAP.get(key_text, key_text)
                    result[key_en] = value
                    i += 2
                else:
                    i += 1

    return result


def format_detail_markdown(detail: Dict[str, Any], reg_no: str) -> str:
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


# --- Statistics ---

def parse_statistics_json(html: str) -> Dict[str, Any]:
    """Parse statistics page into structured JSON."""
    soup = BeautifulSoup(html, "lxml")
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
    return stats


def format_stats_markdown(soup) -> str:
    """Format statistics page content as markdown."""
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
