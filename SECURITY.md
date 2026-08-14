# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in Nexus, please report it responsibly.

**Do not open a public GitHub issue for security vulnerabilities.**

Instead, email: **[your-email@example.com]** with:
- Description of the vulnerability
- Steps to reproduce
- Potential impact

You should receive a response within 48 hours.

## Security Measures

Nexus implements the following security practices:

- **Authentication** — JWT with audience/issuer validation, bcrypt password hashing
- **Authorization** — Per-user session isolation, organization-scoped data
- **Encryption** — Fernet symmetric encryption for stored credentials
- **Input validation** — Pydantic schemas, SQL query validation, message length limits
- **Rate limiting** — Per-IP request throttling
- **Security headers** — X-Content-Type-Options, X-Frame-Options, HSTS, Referrer-Policy
- **Prompt injection defense** — External content treated as untrusted
- **Docker** — Non-root containers, minimal attack surface
- **Secrets** — `.env` files gitignored, no hardcoded credentials

## Dependencies

Run `pip audit` and `npm audit` regularly to check for known vulnerabilities in dependencies.

## Scope

This security policy applies to the latest release of Nexus. If you're using an older version, please upgrade before reporting.
