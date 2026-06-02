#!/usr/bin/env python3
"""
MCP Server for China Drug Clinical Trial Registration Platform
(药物临床试验登记与信息公示平台 - chinadrugtrials.org.cn)

Operated by NMPA Center for Drug Evaluation (CDE).
Uses Playwright for browser automation due to JavaScript anti-bot protection.

Architecture follows clinicaltrialsgov-mcp-server pattern:
- Modular tools, resources, and prompts
- Service layer with browser lifecycle management
- Declarative error recovery hints
"""

from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP

from chinadrugtrials_mcp.browser_manager import browser_mgr
from chinadrugtrials_mcp.schemas import (
    SearchTrialsInput,
    GetTrialDetailInput,
    GetStatisticsInput,
)
from chinadrugtrials_mcp.tools import (
    chinadrugtrials_search_trials,
    chinadrugtrials_get_trial_detail,
    chinadrugtrials_get_statistics,
)
from chinadrugtrials_mcp.resources import get_trial_resource
from chinadrugtrials_mcp.prompts import analyze_china_trial_landscape


# --- Lifespan ---

@asynccontextmanager
async def app_lifespan(app):
    """Manage browser lifecycle across the MCP server session."""
    yield {}
    try:
        await browser_mgr.cleanup()
    except Exception:
        pass


# --- MCP Server ---

mcp = FastMCP("chinadrugtrials_mcp", lifespan=app_lifespan)


# --- Tools (3) ---

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
async def tool_search_trials(params: SearchTrialsInput) -> str:
    """Search clinical trials on China's Drug Clinical Trial Registration Platform (chinadrugtrials.org.cn).

    Operated by NMPA/CDE, this is China's primary public registry for drug clinical trials,
    analogous to ClinicalTrials.gov in the US. Supports searching by drug name, registration
    number, indication, sponsor, PI, trial site, drug type, and trial status.
    """
    return await chinadrugtrials_search_trials(params)


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
async def tool_get_trial_detail(params: GetTrialDetailInput) -> str:
    """Get detailed information for a specific clinical trial from China's Drug Clinical Trial Registration Platform.

    Provide a registration number (e.g., CTR20261395) to retrieve full trial details including
    sponsor info, trial phase, drug details, enrollment targets, and more.
    """
    return await chinadrugtrials_get_trial_detail(params)


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
async def tool_get_statistics(params: GetStatisticsInput) -> str:
    """Get clinical trial registration statistics from China's Drug Clinical Trial Registration Platform.

    Displays aggregate statistics about registered trials including counts by drug type,
    trial phase, and other dimensions.
    """
    return await chinadrugtrials_get_statistics(params)


# --- Resources (1) ---

@mcp.resource("chinadrugtrials://{reg_no}")
async def resource_trial_detail(reg_no: str) -> str:
    """Fetch a single China clinical trial by CTR registration number.

    URI format: chinadrugtrials://CTR{YYYY}{NNNN}
    Example: chinadrugtrials://CTR20261395

    Returns markdown-formatted trial detail including sponsor, drug, phase, enrollment, etc.
    """
    return await get_trial_resource(reg_no)


# --- Prompts (1) ---

@mcp.prompt()
async def prompt_analyze_landscape(topic: str, focus_areas: str = "") -> str:
    """Guide structured analysis of the China clinical trial landscape for a given topic.

    Helps researchers, QA professionals, and business analysts understand:
    - Trial distribution by drug type, phase, and status
    - Sponsor and investigator landscape
    - Competitive intelligence on therapeutic areas
    - Enrollment progress and trial velocity

    Args:
        topic: Therapeutic area, drug class, or indication (e.g., "PD-1 inhibitors", "肺癌")
        focus_areas: Optional comma-separated dimensions (e.g., "phase_distribution,sponsor_landscape")
    """
    return await analyze_china_trial_landscape(topic, focus_areas)


if __name__ == "__main__":
    mcp.run()
