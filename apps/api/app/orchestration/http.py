"""Shared HTTP helpers: retry with exponential backoff for transient failures,
and user-friendly error mapping. Provider/internal details are logged, never
surfaced to the end user."""

import asyncio
import logging
import random
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

RETRYABLE_STATUS = {429, 502, 503, 504}
NON_RETRYABLE_STATUS = {401, 403, 404}


async def call_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    max_retries: int = 3,
    backoff_seconds: float = 1.0,
    friendly_name: str = "API",
    **kwargs: Any,
) -> httpx.Response:
    """Perform an HTTP request with bounded exponential backoff + jitter.

    Retries only on 429 (honoring Retry-After), transient 5xx, and
    connection/timeout errors. Never retries 401/403/404 or other 4xx.
    """
    attempt = 0
    while True:
        try:
            resp = await client.request(method, url, **kwargs)
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as e:
            attempt += 1
            if attempt > max_retries:
                raise
            wait = _backoff(attempt, backoff_seconds)
            logger.warning(
                "%s connection error (attempt %d), retrying in %.1fs: %s",
                friendly_name,
                attempt,
                wait,
                e,
            )
            await asyncio.sleep(wait)
            continue

        if resp.status_code in NON_RETRYABLE_STATUS or (
            resp.status_code < 500 and resp.status_code != 429
        ):
            return resp

        if resp.status_code in RETRYABLE_STATUS:
            attempt += 1
            if attempt > max_retries:
                return resp
            wait = _retry_after(resp, attempt, backoff_seconds)
            logger.warning(
                "%s returned HTTP %d (attempt %d), retrying in %.1fs",
                friendly_name,
                resp.status_code,
                attempt,
                wait,
            )
            await asyncio.sleep(wait)
            continue

        return resp


def _backoff(attempt: int, base: float) -> float:
    return base * (2 ** (attempt - 1)) + random.uniform(0, base / 2)


def _retry_after(resp: httpx.Response, attempt: int, base: float) -> float:
    raw = resp.headers.get("Retry-After")
    if raw and raw.isdigit():
        return min(int(raw), 60)
    return _backoff(attempt, base)


def friendly_error(
    provider: str,
    exc: Exception,
    *,
    context: str = "request",
    status_code: Optional[int] = None,
    detail: str = "",
) -> Dict[str, Any]:
    """Build a user-facing error payload. Full details go to the logs only."""
    if status_code == 401 or "401" in str(exc):
        return {
            "error": (
                f"{provider} authentication failed. Reconnect the source in "
                "Sources to refresh your credentials."
            )
        }
    if status_code == 403:
        return {
            "error": (
                f"{provider} denied access. The connected account is missing "
                f"the required permissions for this {context}."
            )
        }
    if status_code == 404:
        return {"error": f"{provider} could not find the requested {context}."}
    if status_code == 429:
        return {
            "error": (
                f"{provider} is rate-limiting requests right now. Wait a moment "
                "and try again."
            )
        }
    if status_code is not None and status_code >= 500:
        return {"error": f"{provider} is having a temporary outage. Try again shortly."}
    if isinstance(exc, (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout)):
        return {
            "error": f"Could not reach {provider}. Check your network connection and try again."
        }
    logger.warning(
        "%s %s failed: %s (%s)", provider, context, exc, detail or status_code
    )
    return {"error": f"{provider} {context} failed. Try again."}
