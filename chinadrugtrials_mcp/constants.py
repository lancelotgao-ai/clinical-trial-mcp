"""Shared constants for chinadrugtrials.org.cn MCP server."""

BASE_URL = "https://www.chinadrugtrials.org.cn"
SEARCH_LIST_URL = f"{BASE_URL}/clinicaltrials.searchlist.dhtml"
STATISTICS_URL = f"{BASE_URL}/clinicaltrials.tongji.dhtml"

# Recovery hint messages for error contexts
RECOVERY_HINTS = {
    "not_found": "The requested trial was not found. Try searching with broader criteria or verify the registration number (e.g., CTR20261395).",
    "timeout": "The chinadrugtrials.org.cn server is slow or unresponsive. Wait a moment and retry.",
    "connection": "Network error. Check your internet connection and retry.",
    "playwright": "Playwright browser engine is not ready. Run: pip install playwright && playwright install chromium",
    "page_range": "Page number is out of range. Use the total_pages value from search results.",
    "invalid_reg_no": "Invalid registration number format. Must start with 'CTR' followed by digits (e.g., CTR20261395).",
}
