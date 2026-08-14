# Contributing to Nexus

Thanks for your interest in contributing! Here's how to get started.

## Development Setup

1. Fork and clone the repo
2. Copy `.env.example` to `.env`
3. Start the dev stack: `docker compose up --build`

### Local development (without Docker)

**Backend:**
```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd apps/web
npm install
npm run dev
```

## Code Style

### Python
- Formatter/linter: `ruff`
- Type checker: `mypy`
- Run before committing:
  ```bash
  cd apps/api
  ruff check .
  ruff format .
  mypy app/
  ```

### TypeScript
- Linter: `eslint`
- Run before committing:
  ```bash
  cd apps/web
  npm run lint
  ```

## Pull Requests

1. Create a feature branch from `main`
2. Make your changes
3. Run linters and type checks
4. Write clear commit messages
5. Open a PR with a description of what changed and why

### PR Checklist
- [ ] Code passes linting (`ruff check`, `npm run lint`)
- [ ] No new TypeScript errors
- [ ] No secrets or credentials in code
- [ ] `.env.example` updated if new env vars added
- [ ] Docs updated if API or behavior changed

## Project Layout

- `apps/api/` — FastAPI backend (Python)
- `apps/web/` — React frontend (TypeScript)
- `docs/` — Architecture decision records and guides

## Reporting Issues

Open a GitHub issue with:
- Steps to reproduce
- Expected vs actual behavior
- Environment details (OS, Python/Node version)

For security vulnerabilities, see [SECURITY.md](SECURITY.md).
