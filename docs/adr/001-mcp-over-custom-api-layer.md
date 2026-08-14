# ADR 001: Use the MCP Protocol with the Official SDK

## Status

Accepted (supersedes the initial custom-API approach)

## Context

Nexus needs a standard way for the AI orchestrator to communicate with multiple data source integrations (GitHub, Slack, HubSpot, PostgreSQL). The alternatives are:

1. Custom tool-calling API with proprietary interfaces
2. Model Context Protocol (MCP) using the official SDK
3. Function calling with provider-specific schemas

## Decision

Use the Model Context Protocol (MCP) with the official Python SDK (`mcp==1.29.0`). Each integration is a standalone MCP server process exposing a real `tools/list` / `tools/call` interface over stdio:

- `app/mcp_servers/slack_server.py`
- `app/mcp_servers/github_server.py`
- `app/mcp_servers/hubspot_server.py`
- `app/mcp_servers/postgres_server.py`

The backend spawns and manages these processes through an in-process gateway (`app/orchestration/mcp_client.py`), which routes every tool call as an MCP `tools/call` request and injects the caller's identity as a reserved `__user_id__` argument that the servers strip before dispatch. Because the servers are ordinary stdio MCP servers, any MCP client (e.g. Claude Desktop) can connect to them directly with `python -m app.mcp_servers.<name>`.

On Windows, each server process is terminated explicitly by PID (via a PID-file handshake) on shutdown, because stdio children do not reliably exit when stdin closes.

## Alternatives Considered

### Custom API Layer

Build a proprietary tool-calling interface with custom JSON schemas.

Pros:
- Full control over the interface
- No dependency on external protocols

Cons:
- No ecosystem compatibility
- Must maintain custom documentation
- No community tooling
- Reimplements existing solutions

### Provider-Specific Function Calling

Use OpenAI/Anthropic function calling directly without MCP.

Pros:
- Simpler initial implementation
- Direct provider integration

Cons:
- Tightly couples to specific LLM providers
- No standard tool interface
- Harder to add new tools
- Can't leverage MCP ecosystem

## Tradeoffs

MCP adds a protocol layer but provides:
- Standard tool interface across all integrations
- Ecosystem compatibility with MCP servers
- Clear separation between tool definition and execution
- Independent testability of each integration

## Consequences

- Each integration is an independent MCP server process with a standard entry point
- Adding new integrations follows a standard pattern (`*_tools.py` handler module + `*_server.py` process + gateway route)
- Tool definitions are self-documenting
- Can swap LLM providers without changing tool interfaces
- The test suite verifies MCP discovery parity against the registry and exercises real `tools/call` round-trips
- Initial setup requires understanding MCP patterns
