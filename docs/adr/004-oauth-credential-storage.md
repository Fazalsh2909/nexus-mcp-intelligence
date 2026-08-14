# ADR 004: OAuth Credential Storage

## Status

Accepted

## Context

Nexus connects to OAuth-protected services (GitHub, Slack, HubSpot). OAuth tokens and API keys must be stored securely. The system must handle token refresh, encryption at rest, and prevent credential exposure.

## Decision

Implement a `CredentialService` abstraction with:
1. Fernet symmetric encryption for credentials at rest
2. Encrypted storage in the database
3. No credential exposure to frontend
4. No credential logging
5. Development fallback using environment variables

## Alternatives Considered

### Plaintext Storage

Store credentials as plain text in the database.

Pros:
- Simplest implementation
- Easy debugging

Cons:
- Massive security risk
- Compliance violation
- Database breach exposes all credentials

### External Secret Manager

Use AWS Secrets Manager, HashiCorp Vault, etc.

Pros:
- Industry best practice
- Audit logging
- Automatic rotation

Cons:
- Adds infrastructure dependency
- More complex local development
- Higher cost for small deployments

## Tradeoffs

Fernet encryption provides adequate security for a portfolio project while keeping the implementation self-contained. A production deployment should migrate to an external secret manager.

## Consequences

- Credentials are encrypted with Fernet using a configurable key
- The encryption key must be provided via environment variable
- Token refresh logic is handled per-integration
- Frontend never sees raw tokens
- Structured logs never contain credentials
- A production deployment should use AWS Secrets Manager or equivalent
