"""Core service layer for chinadrugtrials.org.cn interactions."""

import json
from typing import Optional
from urllib.parse import quote

from .browser_manager import browser_mgr
from .constants import SEARCH_LIST_URL, STATISTICS_URL
from .parsers import (
    parse_search_results,
    format_search_markdown,
    parse_detail,
    format_detail_markdown,
    parse_statistics_json,
    format_stats_markdown,
    _handle_error,
)
from .schemas import SearchTrialsInput, GetTrialDetailInput, GetStatisticsInput, ResponseFormat


class ChinadrugtrialsService:
    """Service layer wrapping Playwright browser operations for the CDE registry."""

    async def search_trials(self, params: SearchTrialsInput) -> dict:
        """Search trials and return structured data + formatted markdown."""
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
            param_str = "&".join(f"{k}={quote(v, safe='')}" for k, v in query.items())
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
            data = parse_search_results(content)

            md = format_search_markdown(data)
            js = json.dumps(data, ensure_ascii=False, indent=2)
            return {"data": data, "markdown": md, "json": js}

        except Exception as e:
            err = _handle_error(e)
            return {"error": err, "data": {"trials": [], "pagination": {}}, "markdown": err, "json": json.dumps({"error": err})}
        finally:
            if page:
                try:
                    await browser_mgr.close_page(page)
                except Exception:
                    pass

    async def get_trial_detail(self, params: GetTrialDetailInput) -> dict:
        """Get trial detail and return structured data + formatted markdown."""
        page = None
        try:
            page = await browser_mgr.get_page()
            search_url = f"{SEARCH_LIST_URL}?reg_no={quote(params.reg_no, safe='')}&indication=&case_no=&drugs_name=&drugs_type=&appliers=&communities=&researchers=&agencies=&state="
            await page.goto(search_url, wait_until="domcontentloaded", timeout=60000)

            try:
                await page.wait_for_selector("table.table, table", timeout=30000)
            except Exception:
                pass

            content = await page.content()
            if params.reg_no not in content:
                err_msg = f"Trial `{params.reg_no}` was not found. Verify the registration number (e.g., CTR20261395)."
                return {
                    "error": err_msg,
                    "data": {},
                    "markdown": f"# Trial Not Found\n\n{err_msg}",
                    "json": json.dumps({"error": err_msg}),
                }

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

            detail = parse_detail(detail_content)
            md = format_detail_markdown(detail, params.reg_no)
            js = json.dumps(detail, ensure_ascii=False, indent=2)
            return {"data": detail, "markdown": md, "json": js}

        except Exception as e:
            err = _handle_error(e)
            return {"error": err, "data": {}, "markdown": err, "json": json.dumps({"error": err})}
        finally:
            if page:
                try:
                    await browser_mgr.close_page(page)
                except Exception:
                    pass

    async def get_statistics(self, params: GetStatisticsInput) -> dict:
        """Get statistics and return structured data + formatted markdown."""
        page = None
        try:
            page = await browser_mgr.get_page()
            await page.goto(STATISTICS_URL, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(3000)

            content = await page.content()
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, "lxml")

            data = parse_statistics_json(content)
            md = format_stats_markdown(soup)
            js = json.dumps(data, ensure_ascii=False, indent=2)
            return {"data": data, "markdown": md, "json": js}

        except Exception as e:
            err = _handle_error(e)
            return {"error": err, "data": {}, "markdown": err, "json": json.dumps({"error": err})}
        finally:
            if page:
                try:
                    await browser_mgr.close_page(page)
                except Exception:
                    pass


# Service singleton
_service: Optional[ChinadrugtrialsService] = None


def get_service() -> ChinadrugtrialsService:
    """Get or create the singleton service instance."""
    global _service
    if _service is None:
        _service = ChinadrugtrialsService()
    return _service
