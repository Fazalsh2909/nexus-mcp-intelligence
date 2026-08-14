"""Shared helpers for the integration MCP servers."""

import json
import os
from typing import Any, Awaitable, Callable, Dict, List

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

Executor = Callable[..., Awaitable[Dict[str, Any]]]


def _register_pid() -> None:
    """Write this process's PID where the gateway can find it, so the parent
    can terminate the child reliably (Windows children do not always exit
    when stdin closes)."""
    pidfile = os.environ.get("NEXUS_MCP_PIDFILE")
    if pidfile:
        try:
            with open(pidfile, "w") as f:
                f.write(str(os.getpid()))
        except OSError:
            pass


def build_server(
    name: str, tools_spec: List[Dict[str, Any]], executor: Executor
) -> Server:
    server = Server(name)

    @server.list_tools()
    async def list_tools() -> List[Tool]:
        return [
            Tool(
                name=t["function"]["name"],
                description=t["function"].get("description"),
                inputSchema=t["function"].get(
                    "parameters", {"type": "object", "properties": {}}
                ),
            )
            for t in tools_spec
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        args = dict(arguments or {})
        user_id = str(args.pop("__user_id__", "") or "")
        organization_id = str(args.pop("__organization_id__", "") or "")

        from app.db.session import async_session

        async with async_session() as session:
            result = await executor(
                name,
                args,
                user_id=user_id,
                organization_id=organization_id,
                db=session,
            )
        return [TextContent(type="text", text=json.dumps(result, default=str))]

    return server


async def run(server: Server) -> None:
    _register_pid()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )
