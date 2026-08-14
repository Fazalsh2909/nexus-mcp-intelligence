import sys
from typing import List
from pydantic_settings import BaseSettings


INSECURE_DEFAULTS = {
    "JWT_SECRET": {
        "change-me-in-production",
        "change-me-in-production-use-openssl-rand-base64-32",
        "",
    },
    "ENCRYPTION_KEY": {
        "change-me-use-fernet-key",
        "change-me-use-fernet-key-generate",
        "",
    },
}


class Settings(BaseSettings):
    FRONTEND_URL: str = "http://localhost:5173"
    API_URL: str = "http://localhost:8000"

    DATABASE_URL: str = "postgresql+asyncpg://nexus:nexus_dev@localhost:5432/nexus"
    REDIS_URL: str = "redis://localhost:6379/0"

    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = 60
    JWT_AUDIENCE: str = "nexus"
    JWT_ISSUER: str = "nexus-api"

    ENCRYPTION_KEY: str = "change-me-use-fernet-key"

    LLM_PROVIDER: str = "openai"
    LLM_MODEL: str = "gpt-4o"
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    GITHUB_REDIRECT_URI: str = "http://localhost:8000/api/v1/sources/github/callback"
    GITHUB_PERSONAL_ACCESS_TOKEN: str = ""

    SLACK_CLIENT_ID: str = ""
    SLACK_CLIENT_SECRET: str = ""
    SLACK_REDIRECT_URI: str = "http://localhost:8000/api/v1/sources/slack/callback"
    SLACK_BOT_TOKEN: str = ""

    HUBSPOT_CLIENT_ID: str = ""
    HUBSPOT_CLIENT_SECRET: str = ""
    HUBSPOT_REDIRECT_URI: str = "http://localhost:8000/api/v1/sources/hubspot/callback"
    HUBSPOT_ACCESS_TOKEN: str = ""

    MCP_POSTGRES_HOST: str = "localhost"
    MCP_POSTGRES_PORT: int = 5432
    MCP_POSTGRES_USER: str = ""
    MCP_POSTGRES_PASSWORD: str = ""
    MCP_POSTGRES_DB: str = "nexus"

    CORS_ORIGINS: List[str] = ["http://localhost:5173"]
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000

    LOG_LEVEL: str = "INFO"
    ENABLE_METRICS: bool = True

    MAX_TOOL_CALLS_PER_REQUEST: int = 20
    MAX_COST_PER_REQUEST: float = 0.50
    MAX_MESSAGE_LENGTH: int = 10000

    APP_NAME: str = "Nexus"
    DATABASE_URL_SYNC: str = ""
    POSTGRES_USER: str = ""
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


settings = Settings()


def validate_security_settings():
    errors = []

    if settings.JWT_SECRET in INSECURE_DEFAULTS["JWT_SECRET"]:
        errors.append(
            "JWT_SECRET is set to an insecure default. "
            'Generate a real secret: python -c "import secrets; print(secrets.token_urlsafe(32))"'
        )

    if settings.ENCRYPTION_KEY in INSECURE_DEFAULTS["ENCRYPTION_KEY"]:
        errors.append(
            "ENCRYPTION_KEY is set to an insecure default. "
            'Generate a real key: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
        )

    if errors:
        print("\n" + "=" * 60, file=sys.stderr)
        print("SECURITY VALIDATION FAILED", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        for i, err in enumerate(errors, 1):
            print(f"\n  {i}. {err}", file=sys.stderr)
        print("\n" + "=" * 60 + "\n", file=sys.stderr)
        raise SystemExit(1)
