"""PostgreSQL MCP server. Run: python -m app.mcp_servers.postgres_server"""

import asyncio

from app.mcp_servers.base import build_server, run
from app.orchestration.tools_postgres import execute_postgres_tool, postgres_tools


async def _executor(
    tool_name: str,
    arguments: dict,
    user_id: str = "",
    organization_id: str = "",
    db=None,
) -> dict:
    return await execute_postgres_tool(tool_name, arguments)


server = build_server("postgres", postgres_tools, _executor)

if __name__ == "__main__":
    asyncio.run(run(server))
