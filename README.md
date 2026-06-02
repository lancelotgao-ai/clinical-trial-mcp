# chinadrugtrials-mcp

MCP Server for China Drug Clinical Trial Registration and Information Disclosure Platform (药物临床试验登记与信息公示平台, chinadrugtrials.org.cn).

## Overview

Provides tools to search and retrieve clinical trial data registered with China's NMPA/CDE.

Inspired by [clinicaltrialsgov-mcp-server](https://github.com/cyanheads/clinicaltrialsgov-mcp-server) architecture.

## Capabilities

### Tools (3)

| Tool | Description |
|------|-------------|
| `chinadrugtrials_search_trials` | Search clinical trials by drug name, indication, registration number, sponsor, PI, trial site, status, drug type |
| `chinadrugtrials_get_trial_detail` | Get detailed information for a specific trial by its registration number (e.g., CTR20261395) |
| `chinadrugtrials_get_statistics` | View clinical trial registration statistics from the platform |

### Resources (1)

| Resource | URI Pattern | Description |
|----------|-------------|-------------|
| Trial Detail | `chinadrugtrials://{reg_no}` | Direct access to a single trial by CTR registration number |

### Prompts (1)

| Prompt | Description |
|--------|-------------|
| `analyze_china_trial_landscape` | Guided analysis of the China clinical trial landscape for a given therapeutic area or drug class |

## Architecture

```
chinadrugtrials-mcp/
├── server.py                    # Entry point (FastMCP initialization)
├── chinadrugtrials_mcp/
│   ├── __init__.py
│   ├── constants.py             # URLs, recovery hints
│   ├── schemas.py               # Pydantic input/output models
│   ├── browser_manager.py       # Playwright browser lifecycle
│   ├── parsers.py               # HTML parsing + formatting utilities
│   ├── services.py              # Core service layer (HTTP/browser ops)
│   ├── tools.py                 # Tool handler implementations
│   ├── resources.py             # Resource handler implementations
│   └── prompts.py               # Prompt template implementations
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Technical Notes

- Uses Playwright for browser automation due to JavaScript anti-bot protection on the target site.
- The site renders search results as full HTML pages (server-side rendering after JS anti-bot challenge).
- Trial detail pages use session-based POST requests, so the full browser context is needed.
- Service layer provides retry-friendly error handling with recovery hints.

## Installation

```bash
# Install package (editable)
pip install -e .

# Or install dependencies manually
pip install mcp httpx beautifulsoup4 lxml playwright pydantic

# Install Playwright browser
playwright install chromium
```

## Configuration (WorkBuddy MCP)

Add to `~/.workbuddy/mcp.json`:

```json
{
  "mcpServers": {
    "chinadrugtrials": {
      "type": "stdio",
      "command": "/path/to/venv/bin/python",
      "args": ["/path/to/chinadrugtrials-mcp/server.py"]
    }
  }
}
```

## Registration Number Format

China drug trial registration numbers follow the pattern: `CTR{YYYY}{NNNN}`

Examples: `CTR20261395`, `CTR20240001`
