"""MCP gateway: spawns the per-provider MCP server processes over stdio and
routes every integration tool call through the MCP protocol.

Each tool call is an MCP `tools/call` request handled by a separate process;
the caller's identity is passed as a reserved argument (`__user_id__`) which
the server strips before dispatching to the underlying tool.
"""

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import get_default_environment, stdio_client

API_ROOT = Path(__file__).resolve().parents[2]

# server key -> (module to spawn, tool name prefix)
SERVER_MODULES: Dict[str, Tuple[str, str]] = {
    "slack": ("app.mcp_servers.slack_server", "slack_"),
    "github": ("app.mcp_servers.github_server", "github_"),
    "hubspot": ("app.mcp_servers.hubspot_server", "hubspot_"),
    "postgres": ("app.mcp_servers.postgres_server", "postgres_"),
}

_sessions: Dict[str, Dict[str, Any]] = {}
_locks: Dict[str, asyncio.Lock] = {}


def _route(tool_name: str) -> Optional[str]:
    for server_name, (_module, prefix) in SERVER_MODULES.items():
        if tool_name.startswith(prefix):
            return server_name
    return None


async def _wait_for_pid(path: str, timeout: float = 8.0) -> Optional[int]:
    """The server child writes its PID to a file shortly after boot."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with open(path) as f:
                pid = int(f.read().strip())
            if pid:
                return pid
        except (OSError, ValueError):
            pass
        await asyncio.sleep(0.05)
    return None


def _kill_pid(pid: int) -> None:
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            timeout=10,
        )
    else:  # pragma: no cover
        try:
            os.kill(pid, 15)
        except OSError:
            pass


async def _open_process(server_name: str) -> Dict[str, Any]:
    """Spawn a server subprocess and connect an MCP session to it.

    The transport async generator is entered AND exited inside a single
    dedicated manager task, so anyio's task-group cancel scope always sees
    the same host task and the generator is never garbage-collected while
    open (GC would close it from the loop's finalizer task, which breaks
    anyio and cancels unrelated awaits on this platform).
    """
    module, _prefix = SERVER_MODULES[server_name]

    state: Dict[str, Any] = {"pid": None}
    ready = asyncio.Event()
    stop = asyncio.Event()
    state["stop"] = stop

    async def manager() -> None:
        pidfile: Optional[str] = None
        env: Optional[Dict[str, str]] = None
        if sys.platform == "win32":
            fd, pidfile = tempfile.mkstemp(prefix="nexus_mcp_", suffix=".pid")
            os.close(fd)
            env = {**get_default_environment(), "NEXUS_MCP_PIDFILE": pidfile}
        try:
            async with stdio_client(
                StdioServerParameters(
                    command=sys.executable,
                    args=["-m", module],
                    cwd=str(API_ROOT),
                    env=env,
                )
            ) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    state["session"] = session
                    state["pidfile"] = pidfile
                    state["pid"] = await _wait_for_pid(pidfile) if pidfile else None
                    ready.set()
                    await stop.wait()
        except BaseException as exc:
            state["error"] = exc
            ready.set()
            raise

    state["task"] = asyncio.create_task(manager())
    await ready.wait()
    if "error" in state:
        await asyncio.gather(state["task"], return_exceptions=True)
        raise state["error"]
    return state


async def _close_process(entry: Dict[str, Any]) -> None:
    pid = entry.get("pid")
    if pid:
        # The SDK waits for the child to exit on its own, which Windows
        # children may never do; kill it explicitly first.
        try:
            await asyncio.to_thread(_kill_pid, pid)
        except Exception:
            pass
    entry["stop"].set()
    try:
        await asyncio.wait_for(asyncio.shield(entry["task"]), timeout=10)
    except BaseException:
        entry["task"].cancel()
    pidfile = entry.get("pidfile")
    if pidfile:
        try:
            os.remove(pidfile)
        except OSError:
            pass


async def _get_session(server_name: str) -> Dict[str, Any]:
    lock = _locks.setdefault(server_name, asyncio.Lock())
    async with lock:
        cached = _sessions.get(server_name)
        if cached is not None:
            return cached
        entry = await _open_process(server_name)
        _sessions[server_name] = entry
        return entry


async def _drop_session(server_name: str) -> None:
    lock = _locks.get(server_name)
    if lock is None:
        return
    async with lock:
        entry = _sessions.pop(server_name, None)
        if entry is not None:
            await _close_process(entry)


async def close_all() -> None:
    """Close every server process and its MCP session. Call on shutdown."""
    for server_name in list(_sessions.keys()):
        await _drop_session(server_name)


async def discover_tools() -> List[Dict[str, Any]]:
    """Query every MCP server for its tool list (real MCP list_tools calls)."""
    discovered: List[Dict[str, Any]] = []
    for server_name in SERVER_MODULES:
        entry = await _get_session(server_name)
        tools = await entry["session"].list_tools()
        for t in tools.tools:
            discovered.append(
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description or "",
                        "parameters": t.inputSchema,
                    },
                }
            )
    return discovered


async def call_tool(
    tool_name: str, arguments: Dict[str, Any], user_id: str = ""
) -> Dict[str, Any]:
    """Invoke a tool through its provider MCP server."""
    server_name = _route(tool_name)
    if server_name is None:
        raise ValueError(f"Unknown tool: {tool_name}")

    payload = dict(arguments)
    payload["__user_id__"] = user_id

    last_error: Optional[Exception] = None
    for attempt in range(2):
        try:
            entry = await _get_session(server_name)
            result = await entry["session"].call_tool(tool_name, payload)
            break
        except Exception as e:  # dead subprocess -> respawn once
            last_error = e
            await _drop_session(server_name)
    else:
        return {"error": f"The {server_name} integration failed: {last_error}"}

    text = "".join(getattr(item, "text", "") for item in (result.content or []))
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = {"result": text}
    if result.isError and not isinstance(parsed, dict):
        return {"error": str(parsed)}
    return parsed
