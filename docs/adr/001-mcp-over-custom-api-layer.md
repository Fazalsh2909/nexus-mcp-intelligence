# ADR 001: Use MCP Over Custom API Layer

## Status

Accepted

## Context

Nexus needs a standard way for the AI orchestrator to communicate with multiple data source integrations (GitHub, Slack, HubSpot, PostgreSQL). The alternatives are:

1. Custom tool-calling API with proprietary interfaces
2. Model Context Protocol (MCP) using the official SDK
3. Function calling with provider-specific schemas

## Decision

Use the Model Context Protocol (MCP) with the official `@modelcontextprotocol/sdk` TypeScript SDK.

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

- Each integration is an independent MCP tool module
- Adding new integrations follows a standard pattern
- Tool definitions are self-documenting
- Can swap LLM providers without changing tool interfaces
- Initial setup requires understanding MCP patterns
