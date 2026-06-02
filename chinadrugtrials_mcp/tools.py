"""Tool definitions for chinadrugtrials.org.cn MCP server.

Each tool follows the clinicaltrialsgov-mcp-server pattern:
- declarative annotations (readOnly, idempotent, openWorld)
- recovery hints for error contexts
- separation of handler logic and formatting
"""

from .schemas import SearchTrialsInput, GetTrialDetailInput, GetStatisticsInput, ResponseFormat
from .services import get_service


async def chinadrugtrials_search_trials(params: SearchTrialsInput) -> str:
    """Search clinical trials on China's Drug Clinical Trial Registration Platform.

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
            - page (int): Page number (default 1, ~20 results/page)
            - response_format: 'markdown' or 'json'

    Returns:
        str: Paginated trial list with reg_no, status, drug_name, indication, title.
    """
    service = get_service()
    result = await service.search_trials(params)
    if "error" in result:
        return result["error"]
    return result["json"] if params.response_format == ResponseFormat.JSON else result["markdown"]


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
    service = get_service()
    result = await service.get_trial_detail(params)
    if "error" in result:
        return result["error"]
    return result["json"] if params.response_format == ResponseFormat.JSON else result["markdown"]


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
    service = get_service()
    result = await service.get_statistics(params)
    if "error" in result:
        return result["error"]
    return result["json"] if params.response_format == ResponseFormat.JSON else result["markdown"]
