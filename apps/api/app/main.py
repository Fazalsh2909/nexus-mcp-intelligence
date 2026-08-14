from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from collections import defaultdict
import time

from app.core.config import settings, validate_security_settings
from app.db.session import engine
from app.api import auth, chat, sources, analytics, health, evaluations
from app.core.logging import setup_logging

validate_security_settings()


rate_limit_store: dict[str, list[float]] = defaultdict(list)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    yield
    await engine.dispose()


app = FastAPI(
    title="Nexus API",
    description="Enterprise MCP Intelligence Platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if settings.API_URL.startswith("https"):
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
    return response


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    window = 60

    rate_limit_store[client_ip] = [
        t for t in rate_limit_store[client_ip] if now - t < window
    ]

    if len(rate_limit_store[client_ip]) >= settings.RATE_LIMIT_PER_MINUTE:
        return Response(
            content='{"detail":"Rate limit exceeded"}',
            status_code=429,
            media_type="application/json",
        )

    rate_limit_store[client_ip].append(now)
    return await call_next(request)


app.include_router(health.router, tags=["health"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(sources.router, prefix="/api/v1/sources", tags=["sources"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])
app.include_router(
    evaluations.router, prefix="/api/v1/evaluations", tags=["evaluations"]
)
