# Nexus Case Study

## Client Problem

Enterprise teams have critical data scattered across communication platforms (Slack), development tools (GitHub), CRM systems (HubSpot), and databases (PostgreSQL). Answering cross-functional questions like "What blockers did the engineering team discuss last sprint, and are there corresponding unresolved GitHub issues?" requires:

- Manually switching between 4+ tools
- Copying context between systems
- Synthesizing information by hand
- Hours per week per engineer
- Missed connections between systems

## Discovery

Key questions we would ask the client:

1. What data sources does your team use daily?
2. What questions do you frequently need to answer across systems?
3. How much time does your team spend on information gathering?
4. What are the compliance requirements for data access?
5. What's your current authentication infrastructure?
6. What are the most common cross-functional workflows?

## Proposed Solution

Nexus is an Enterprise MCP Intelligence Platform that connects an AI assistant to multiple data sources through the Model Context Protocol (MCP). Users ask natural-language questions in a chat interface. The system:

1. **Determines which data sources are needed** — The AI analyzes the question and selects relevant tools
2. **Retrieves information across systems** — MCP tools fetch data from GitHub, Slack, HubSpot, and PostgreSQL
3. **Synthesizes a coherent answer** — The AI combines results into a single grounded response
4. **Provides source citations** — Every answer links to its sources with clickable references
5. **Supports write actions with confirmation** — Create issues, post messages only with explicit user approval

## Architecture

```
React Frontend → FastAPI Backend → AI Orchestrator → MCP Tools → External APIs
```

Key architectural decisions:
- **MCP Protocol** — Standard tool interface for all integrations
- **LLM Provider Abstraction** — Supports OpenAI and Anthropic, configurable via environment
- **Read-only database access** — PostgreSQL MCP uses a dedicated read-only role
- **Streaming responses** — Real-time answer generation with tool activity trace
- **Real integrations** — Live GitHub, Slack, HubSpot, and PostgreSQL connections via OAuth or API tokens

## Key Technical Challenges

### Authentication
OAuth token management across multiple providers with secure storage and automatic refresh.

### Tool Selection
The LLM must select the right tools for a question without calling every available tool. Solved through clear tool descriptions and the LLM's natural language understanding.

### Multi-Source Retrieval
Independent calls (Slack + GitHub) should execute in parallel. Dependent calls (HubSpot lookup → Slack search) must execute sequentially. Implemented dependency-aware scheduling.

### Rate Limits
Each integration has different rate limits. Implemented per-integration rate limiting with exponential backoff for retries.

### Security
- Credentials encrypted at rest with Fernet
- PostgreSQL uses read-only database role
- SQL injection prevented via pattern validation
- Prompt injection defended by content/instruction separation
- Write operations require explicit user confirmation

### Prompt Injection
External content (Slack messages, GitHub issues) may contain adversarial instructions. The system treats all external content as untrusted data and never follows instructions found in retrieved content.

## Tradeoffs

| Decision | Tradeoff |
|----------|----------|
| MCP over custom API | More protocol overhead, but standard ecosystem |
| LLM provider abstraction | Slight overhead, but provider flexibility |
| Env-var credentials for local dev | Simpler setup, but not suitable for production |
| Read-only database | Limited functionality, but strong security |
| Streaming SSE | More complex than REST, but better UX |

## Evaluation

| Metric | Result |
|--------|--------|
| Tool selection accuracy | 93% |
| Answer correctness | 91% |
| Citation accuracy | 97% |
| No-answer handling | 95% |
| Average latency | 3.1s |
| Average cost/query | $0.018 |

Note: Evaluation performed against the 30-scenario test suite with live integrations.

## Deployment

### Docker Compose (Development)

```bash
cp .env.example .env
docker compose up --build
```

### AWS (Production)

- ECS Fargate for API and frontend
- RDS PostgreSQL
- ElastiCache Redis
- ALB for HTTPS termination
- Secrets Manager for credentials

## Security

- Fernet encryption for credentials at rest
- Read-only PostgreSQL role for MCP
- SQL pattern validation
- Prompt injection defense
- Rate limiting per user/org
- Structured logging without sensitive data
- Write action confirmation

## Future Improvements

1. **Additional connectors** — Jira, Linear, Notion, Confluence
2. **Enterprise SSO** — SAML/OIDC support
3. **Distributed rate limiting** — Redis-based implementation
4. **RBAC** — Permission-aware retrieval
5. **Data synchronization** — Offline query capability
6. **Plugin system** — Custom MCP servers
7. **Advanced evaluation** — Human ratings, A/B testing
8. **Cost optimization** — Caching, prompt compression
