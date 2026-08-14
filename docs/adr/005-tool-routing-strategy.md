# ADR 005: Tool Routing Strategy

## Status

Accepted

## Context

The AI orchestrator receives a user question and must determine which tools to call, in what order, and how to combine results. The routing strategy affects answer quality, latency, and cost.

## Decision

Implement a two-phase routing strategy:

1. **Tool Selection Phase** — The LLM receives tool definitions and selects which tools to call based on the user's question
2. **Execution Phase** — Selected tools are executed with dependency-aware scheduling:
   - Independent tools execute in parallel
   - Dependent tools execute sequentially
   - Results are accumulated and passed back to the LLM for synthesis

## Alternatives Considered

### Rule-Based Routing

Use keyword matching to determine which tools to call.

Pros:
- Deterministic
- Fast
- No LLM cost for routing

Cons:
- Brittle for complex queries
- Can't handle nuanced questions
- Requires manual rule maintenance

### Single-Step Tool Calling

Call tools one at a time, letting the LLM decide after each result.

Pros:
- Maximum flexibility
- Each step is informed by previous results

Cons:
- Higher latency (sequential)
- More LLM calls = higher cost
- May over-fetch information

## Tradeoffs

The LLM-driven approach handles complex cross-source queries naturally. The dependency-aware execution prevents unnecessary sequential delays while maintaining correct ordering.

## Consequences

- The LLM sees all available tools and selects the relevant ones
- Independent calls (e.g., Slack search + GitHub search) execute concurrently
- Dependent calls (e.g., HubSpot lookup → Slack search by email) execute sequentially
- Tool results are accumulated and passed to the LLM for synthesis
- The orchestrator enforces rate limits, timeouts, and budget constraints
- Every tool call is logged for observability
