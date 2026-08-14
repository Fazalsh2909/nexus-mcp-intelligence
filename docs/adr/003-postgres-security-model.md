# ADR 003: PostgreSQL Security Model

## Status

Accepted

## Context

The AI assistant needs to query PostgreSQL databases on behalf of users. Unrestricted SQL access is a critical security risk — the LLM could execute destructive operations, access unauthorized data, or perform SQL injection attacks.

## Decision

Implement a multi-layered security model for PostgreSQL MCP tools:

1. **Read-only database role** — The MCP connection uses a dedicated `nexus_readonly` database user with SELECT-only permissions
2. **SQL validation** — All queries are validated against a blocklist of dangerous patterns before execution
3. **Parameterized queries** — Only parameterized SELECT statements are allowed
4. **Query timeout** — Queries are killed after a configurable timeout
5. **Row limits** — Results are capped at a configurable maximum
6. **Table allowlist** — Only whitelisted tables are accessible

## Alternatives Considered

### Full SQL Access

Allow the LLM to run any SQL.

Pros:
- Maximum flexibility
- No restrictions on queries

Cons:
- Destructive operations possible
- SQL injection risk
- Data exfiltration risk
- Compliance violations

### API-Only Access

Expose data through custom API endpoints only.

Pros:
- Full control over data access
- Easy to audit

Cons:
- Must anticipate every query pattern
- High development overhead
- Doesn't leverage SQL flexibility

## Tradeoffs

The security model restricts some query patterns but prevents:
- Data modification (INSERT/UPDATE/DELETE)
- Schema changes (DROP/ALTER/TRUNCATE)
- Unbounded result sets
- Query execution beyond timeout
- Access to non-allowed tables

## Consequences

- The AI can only read data, never modify it
- Complex analytical queries may be blocked by pattern matching
- Users who need write access must use explicit tool calls with confirmation
- The security model is documented and testable
- A real deployment should use PostgreSQL row-level security policies in addition to the application-level checks
