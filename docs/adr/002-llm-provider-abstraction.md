# ADR 002: LLM Provider Abstraction

## Status

Accepted

## Context

The system must support multiple LLM providers (OpenAI, Anthropic) and allow switching between them without code changes. The provider choice should be configurable via environment variables.

## Decision

Create an abstract `LLMProvider` base class with concrete implementations for each provider. The orchestrator depends only on the abstract interface.

## Alternatives Considered

### Direct Provider Usage

Call OpenAI/Anthropic SDKs directly in the orchestration layer.

Pros:
- Simpler code
- Fewer abstractions

Cons:
- Provider lock-in
- Duplicated logic for tool formatting
- Harder to test
- Can't switch providers without code changes

### Use LangChain/LlamaIndex

Use an existing orchestration framework.

Pros:
- Battle-tested abstractions
- Many integrations

Cons:
- Heavy dependencies
- Less control over behavior
- Framework lock-in
- Over-engineered for this use case

## Tradeoffs

The abstraction adds a thin layer but provides:
- Provider-agnostic orchestration
- Easy to add new providers
- Simpler testing with mock providers
- Environment-driven configuration

## Consequences

- Tests use mock provider objects without API keys
- Adding a new provider requires implementing one class
- Orchestration logic never references specific providers
- Provider-specific tool formatting is handled within each provider
