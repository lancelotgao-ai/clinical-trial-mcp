"""Resource definitions for chinadrugtrials.org.cn MCP server.

Resources provide URI-addressable data, similar to clinicaltrialsgov-mcp-server's
`clinicaltrials://{nctId}` pattern. Here we use `chinadrugtrials://{regNo}`.
"""

from .schemas import ResponseFormat
from .services import get_service
from .parsers import format_detail_markdown, _handle_error


async def get_trial_resource(reg_no: str) -> str:
    """Resource handler for chinadrugtrials://{regNo}.

    Fetches a single clinical trial by its CTR registration number.
    Returns markdown-formatted trial detail.
    """
    try:
        service = get_service()
        from .schemas import GetTrialDetailInput
        params = GetTrialDetailInput(reg_no=reg_no, response_format=ResponseFormat.MARKDOWN)
        result = await service.get_trial_detail(params)
        if "error" in result:
            return result["error"]
        return result["markdown"]
    except Exception as e:
        return _handle_error(e)
