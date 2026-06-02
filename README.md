# chinadrugtrials-mcp

MCP Server for China Drug Clinical Trial Registration and Information Disclosure Platform (药物临床试验登记与信息公示平台, chinadrugtrials.org.cn).

## Overview

Provides tools to search and retrieve clinical trial data registered with China's NMPA/CDE.

## Tools

### `chinadrugtrials_search_trials`
Search clinical trials by various criteria (drug name, indication, registration number, sponsor, PI, trial site, status, drug type).

### `chinadrugtrials_get_trial_detail`
Get detailed information for a specific trial by its registration number (e.g., CTR20261395).

### `chinadrugtrials_get_statistics`
View clinical trial registration statistics from the platform.

## Technical Notes

- Uses Playwright for browser automation due to JavaScript anti-bot protection on the target site.
- The site renders search results as full HTML pages (server-side rendering after JS anti-bot challenge).
- Trial detail pages use session-based POST requests, so the full browser context is needed.

## Installation

```bash
# Install dependencies
pip install mcp httpx beautifulsoup4 lxml playwright

# Install Playwright browser
playwright install chromium
```

## Configuration (WorkBuddy MCP)

Add to `~/.workbuddy/mcp.json`:

```json
{
  "mcpServers": {
    "chinadrugtrials": {
      "command": "python",
      "args": ["/Users/lancelot/WorkBuddy/2026-06-02-13-42-25/chinadrugtrials-mcp/server.py"],
      "env": {}
    }
  }
}
```
