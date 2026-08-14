from typing import Dict, Any

from app.orchestration.tools_slack import slack_tools
from app.orchestration.tools_github import github_tools
from app.orchestration.tools_hubspot import hubspot_tools
from app.orchestration.tools_postgres import postgres_tools

TOOL_DEFINITIONS = slack_tools + github_tools + hubspot_tools + postgres_tools

TOOL_MAP = {}
for tool in TOOL_DEFINITIONS:
    TOOL_MAP[tool["function"]["name"]] = tool


async def execute_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    user_id: str = "",
    organization_id: str = "",
    db=None,
) -> Dict[str, Any]:
    if tool_name.startswith("slack_"):
        from app.orchestration.tools_slack import execute_slack_tool

        return await execute_slack_tool(
            tool_name,
            arguments,
            user_id=user_id,
            organization_id=organization_id,
            db=db,
        )
    elif tool_name.startswith("github_"):
        from app.orchestration.tools_github import execute_github_tool

        return await execute_github_tool(
            tool_name,
            arguments,
            user_id=user_id,
            organization_id=organization_id,
            db=db,
        )
    elif tool_name.startswith("hubspot_"):
        from app.orchestration.tools_hubspot import execute_hubspot_tool

        return await execute_hubspot_tool(
            tool_name,
            arguments,
            user_id=user_id,
            organization_id=organization_id,
            db=db,
        )
    elif tool_name.startswith("postgres_"):
        from app.orchestration.tools_postgres import execute_postgres_tool

        return await execute_postgres_tool(tool_name, arguments)

    raise ValueError(f"Unknown tool: {tool_name}")
