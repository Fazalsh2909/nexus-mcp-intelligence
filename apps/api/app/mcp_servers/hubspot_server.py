"""HubSpot MCP server. Run: python -m app.mcp_servers.hubspot_server"""

import asyncio

from app.mcp_servers.base import build_server, run
from app.orchestration.tools_hubspot import execute_hubspot_tool, hubspot_tools

server = build_server("hubspot", hubspot_tools, execute_hubspot_tool)

if __name__ == "__main__":
    asyncio.run(run(server))
