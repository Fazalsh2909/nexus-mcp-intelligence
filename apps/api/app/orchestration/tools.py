from typing import Dict, Any

from app.orchestration.tools_slack import slack_tools
from app.orchestration.tools_github import github_tools
from app.orchestration.tools_hubspot import hubspot_tools
from app.orchestration.tools_postgres import postgres_tools

TOOL_DEFINITIONS = slack_tools + github_tools + hubspot_tools + postgres_tools

TOOL_MAP = {}
for tool in TOOL_DEFINITIONS:
    TOOL_MAP[tool["function"]["name"]] = tool

# Write tools mutate external systems and always require human confirmation.
WRITE_TOOLS = {
    "github_create_issue",
    "hubspot_add_contact_note",
}


async def execute_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    user_id: str = "",
    organization_id: str = "",
    db=None,
) -> Dict[str, Any]:
    """Route a tool call through the provider's MCP server process."""
    from app.orchestration import mcp_client

    if tool_name not in TOOL_MAP:
        raise ValueError(f"Unknown tool: {tool_name}")

    try:
        return await mcp_client.call_tool(tool_name, arguments, user_id=user_id)
    except Exception as e:
        return {"error": f"The {tool_name} integration is unavailable right now: {e}"}
