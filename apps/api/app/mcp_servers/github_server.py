"""GitHub MCP server. Run: python -m app.mcp_servers.github_server"""

import asyncio

from app.mcp_servers.base import build_server, run
from app.orchestration.tools_github import execute_github_tool, github_tools

server = build_server("github", github_tools, execute_github_tool)

if __name__ == "__main__":
    asyncio.run(run(server))
