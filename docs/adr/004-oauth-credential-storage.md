# ADR 004: OAuth Credential Storage and CSRF State

## Status

Accepted

## Context

Nexus connects to OAuth-protected services (GitHub, Slack, HubSpot). OAuth tokens and API keys must be stored securely. The system must handle token refresh, encryption at rest, and prevent credential exposure. The OAuth authorization-code flow also needs protection against CSRF-style authorization hijacking.

## Decision

### Credential storage

1. Fernet symmetric encryption for credentials at rest (`app/core/crypto.py`)
2. Tokens are written to `Connection.encrypted_credentials` only — never to the JSON metadata column (legacy plaintext rows remain read-compatible as a migration aid but are never written)
3. Resolution order: environment variable override → decrypted stored credentials → legacy plaintext metadata
4. No credential exposure to frontend; no credential logging
5. Development fallback using environment variables

### OAuth state

1. Each `authorize` request generates a random 256-bit state value (`secrets.token_urlsafe(32)`)
2. Only its SHA-256 hash is persisted in the `oauth_states` table, with the user, provider, and a 10-minute expiry
3. The callback validates the state (hash match, unexpired, provider match), consumes it atomically (single-use), and binds the resulting connection to the user from the state record — never from the redirect itself
4. Expired records are purged opportunistically

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

### User ID as OAuth State

Pass the user's ID as the OAuth `state` parameter (the earlier approach).

Cons:
- No replay protection — a captured authorize URL is reusable
- State never expires
- No CSRF protection on the callback

## Tradeoffs

Fernet encryption provides adequate security for a portfolio project while keeping the implementation self-contained. A production deployment should migrate to an external secret manager.

## Consequences

- Credentials are encrypted with Fernet using a configurable key (`ENCRYPTION_KEY`)
- OAuth state is single-use, expiring, and stored only as a hash
- The encryption key must be provided via environment variable
- Token refresh logic is handled per-integration
- Frontend never sees raw tokens
- Structured logs never contain credentials
- A production deployment should use AWS Secrets Manager or equivalent
