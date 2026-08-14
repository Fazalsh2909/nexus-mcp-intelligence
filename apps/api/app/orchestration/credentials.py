"""Per-user credential resolution for the integration tools.

Resolution order per integration:
1. Environment variable override (self-hosted deployments)
2. Encrypted credentials stored on the user's Connection row (OAuth)
3. Legacy plaintext metadata (pre-encryption rows, read-only migration aid)

Encrypted payloads are decrypted only in memory for the duration of a call.
"""

from typing import Any, Dict, Optional

from app.core.config import settings
from app.core.crypto import decrypt_credentials


async def _connection(db, user_id: str, integration_type: str):
    if db is None or not user_id:
        return None
    from sqlalchemy import select

    from app.models.models import Connection

    result = await db.execute(
        select(Connection).where(
            Connection.user_id == user_id,
            Connection.integration_type == integration_type,
            Connection.status == "connected",
        )
    )
    return result.scalar_one_or_none()


def _decrypt(conn) -> Optional[Dict[str, Any]]:
    if not conn or not conn.encrypted_credentials:
        return None
    try:
        return decrypt_credentials(conn.encrypted_credentials)
    except ValueError:
        return None


async def resolve_credential(
    db,
    user_id: str,
    integration_type: str,
    env_token: str,
    token_keys: tuple[str, ...],
) -> str:
    """Resolve the primary access token for an integration."""
    if env_token:
        return env_token

    conn = await _connection(db, user_id, integration_type)
    creds = _decrypt(conn)
    if creds:
        for key in token_keys:
            if creds.get(key):
                return str(creds[key])

    # Legacy rows stored tokens in plaintext metadata before encryption.
    if conn and conn.metadata_json:
        for key in token_keys:
            if conn.metadata_json.get(key):
                return str(conn.metadata_json[key])
    return ""


async def resolve_slack_tokens(db, user_id: str) -> Dict[str, str]:
    """Resolve both Slack tokens (bot + user) and workspace metadata."""
    if settings.SLACK_BOT_TOKEN:
        return {"bot_token": settings.SLACK_BOT_TOKEN}

    conn = await _connection(db, user_id, "slack")
    creds = _decrypt(conn)
    if creds:
        return {
            "bot_token": str(creds.get("bot_token") or ""),
            "access_token": str(creds.get("access_token") or ""),
            "team_name": str(creds.get("team_name") or ""),
        }
    if conn and conn.metadata_json:
        return {
            "bot_token": str(conn.metadata_json.get("bot_token") or ""),
            "access_token": str(conn.metadata_json.get("access_token") or ""),
            "team_name": str(conn.metadata_json.get("team_name") or ""),
        }
    return {"bot_token": "", "access_token": "", "team_name": ""}
