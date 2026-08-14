"""MCP server processes (one per integration provider).

Each server speaks the MCP protocol over stdio. The gateway
(app.orchestration.mcp_client) spawns them and routes tool calls through
them, so every integration call crosses a real MCP JSON-RPC boundary.
"""
