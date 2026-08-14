"""Slack MCP server. Run: python -m app.mcp_servers.slack_server"""

import asyncio

from app.mcp_servers.base import build_server, run
from app.orchestration.tools_slack import execute_slack_tool, slack_tools

server = build_server("slack", slack_tools, execute_slack_tool)

if __name__ == "__main__":
    asyncio.run(run(server))
