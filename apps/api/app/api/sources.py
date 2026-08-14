import urllib.parse
import httpx

from fastapi import APIRouter, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.models.models import Connection, User
from app.schemas.schemas import ConnectionResponse
from app.api.auth import get_current_user

router = APIRouter()

OAUTH_SCOPES = {
    "github": "repo read:user",
    "slack": "channels:read channels:history search:read team:read users:read",
    "hubspot": "crm.objects.contacts.read crm.objects.companies.read crm.objects.deals.read",
}

AUTHORIZE_URLS = {
    "github": "https://github.com/login/oauth/authorize",
    "slack": "https://slack.com/oauth/v2/authorize",
    "hubspot": "https://app.hubspot.com/oauth/authorize",
}

TOKEN_URLS = {
    "github": "https://github.com/login/oauth/access_token",
    "slack": "https://slack.com/api/oauth.v2.access",
    "hubspot": "https://api.hubapi.com/oauth/v1/token",
}


def _env_credential(integration_type: str) -> str:
    """Return the configured env credential for a source, if any."""
    return {
        "github": settings.GITHUB_PERSONAL_ACCESS_TOKEN,
        "slack": settings.SLACK_BOT_TOKEN,
        "hubspot": settings.HUBSPOT_ACCESS_TOKEN,
        "postgres": settings.DATABASE_URL,
    }.get(integration_type, "")


@router.get("/", response_model=list[ConnectionResponse])
async def list_connections(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    result = await db.execute(select(Connection).where(Connection.user_id == user.id))
    connections = result.scalars().all()
    by_type = {c.integration_type: c for c in connections}

    changed = False
    for integration_type in ("github", "slack", "hubspot", "postgres"):
        conn = by_type.get(integration_type)
        token = (conn.metadata_json or {}).get("access_token", "") if conn else ""
        bot_token = (conn.metadata_json or {}).get("bot_token", "") if conn else ""
        has_credential = bool(_env_credential(integration_type) or token or bot_token)

        if conn is None:
            if has_credential:
                db.add(
                    Connection(
                        user_id=user.id,
                        integration_type=integration_type,
                        status="connected",
                    )
                )
                changed = True
        elif conn.status == "pending" and not token and not bot_token:
            # A Connect click that never completed OAuth has no credential.
            conn.status = "connected" if has_credential else "disconnected"
            changed = True
        elif conn.status == "disconnected" and has_credential:
            conn.status = "connected"
            changed = True

    if changed:
        await db.commit()
        result = await db.execute(
            select(Connection).where(Connection.user_id == user.id)
        )
        connections = result.scalars().all()

    return connections


@router.get("/{integration_type}/authorize")
async def authorize_source(
    integration_type: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Start OAuth: mark the connection 'pending' and redirect the user to
    the provider's consent screen."""
    if integration_type not in AUTHORIZE_URLS:
        return {"error": f"Unsupported integration: {integration_type}"}

    result = await db.execute(
        select(Connection).where(
            Connection.user_id == user.id,
            Connection.integration_type == integration_type,
        )
    )
    conn = result.scalar_one_or_none()
    if conn is None:
        conn = Connection(
            user_id=user.id,
            integration_type=integration_type,
            status="pending",
        )
        db.add(conn)
    else:
        conn.status = "pending"
    await db.commit()

    if integration_type == "github":
        params = {
            "client_id": settings.GITHUB_CLIENT_ID,
            "redirect_uri": settings.GITHUB_REDIRECT_URI,
            "scope": OAUTH_SCOPES["github"],
            "state": str(user.id),
        }
    elif integration_type == "slack":
        params = {
            "client_id": settings.SLACK_CLIENT_ID,
            "redirect_uri": settings.SLACK_REDIRECT_URI,
            "scope": OAUTH_SCOPES["slack"],
            "state": str(user.id),
        }
    else:
        params = {
            "client_id": settings.HUBSPOT_CLIENT_ID,
            "redirect_uri": settings.HUBSPOT_REDIRECT_URI,
            "scope": OAUTH_SCOPES["hubspot"],
            "state": str(user.id),
        }

    url = f"{AUTHORIZE_URLS[integration_type]}?{urllib.parse.urlencode(params)}"
    return {
        "status": "pending",
        "authorize_url": url,
        "integration_type": integration_type,
    }


@router.get("/{integration_type}/callback")
async def oauth_callback(
    integration_type: str,
    code: str = "",
    state: str = "",
    error: str = "",
    error_description: str = "",
    db: AsyncSession = Depends(get_db),
):
    if error:
        print(f"[sources] {integration_type} OAuth error: {error} {error_description}")
        return RedirectResponse(
            f"{settings.FRONTEND_URL}/sources?error={urllib.parse.quote(error)}"
        )

    client_id = getattr(settings, f"{integration_type.upper()}_CLIENT_ID", "")
    client_secret = getattr(settings, f"{integration_type.upper()}_CLIENT_SECRET", "")
    redirect_uri = getattr(settings, f"{integration_type.upper()}_REDIRECT_URI", "")

    if integration_type == "github":
        token_data = await _exchange(
            TOKEN_URLS["github"],
            {
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
            },
            accept_header="application/json",
        )
        access_token = token_data.get("access_token", "")
    elif integration_type == "slack":
        token_data = await _exchange(
            TOKEN_URLS["slack"],
            {
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
            },
        )
        access_token = token_data.get("access_token", "")
        bot_token = (token_data.get("bot") or {}).get("bot_access_token", "")
        team = token_data.get("team") or {}
    else:
        token_data = await _exchange(
            TOKEN_URLS["hubspot"],
            {
                "client_id": client_id,
                "client_secret": client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        access_token = token_data.get("access_token", "")
        refresh_token = token_data.get("refresh_token", "")

    if not access_token:
        print(f"[sources] {integration_type} token exchange failed: {token_data}")
        return RedirectResponse(
            f"{settings.FRONTEND_URL}/sources?error=token_exchange_failed"
        )

    result = await db.execute(
        select(Connection).where(
            Connection.user_id == str(state),
            Connection.integration_type == integration_type,
        )
    )
    conn = result.scalar_one_or_none()
    if conn is None:
        conn = Connection(
            user_id=str(state),
            integration_type=integration_type,
            status="connected",
        )
        db.add(conn)

    metadata = dict(conn.metadata_json or {})
    metadata["access_token"] = access_token
    if integration_type == "slack":
        metadata["bot_token"] = bot_token or access_token
        metadata["team_name"] = team.get("name", "")
    if integration_type == "hubspot":
        metadata["refresh_token"] = refresh_token
    conn.metadata_json = metadata
    conn.status = "connected"
    await db.commit()

    return RedirectResponse(
        f"{settings.FRONTEND_URL}/sources?connected={integration_type}"
    )


async def _exchange(url: str, payload: dict, accept_header: str = "") -> dict:
    headers = {"Accept": accept_header} if accept_header else {}
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(url, data=payload, headers=headers)
        return resp.json()


@router.post("/{integration_type}/connect")
async def connect_source(
    integration_type: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if integration_type in AUTHORIZE_URLS:
        return await authorize_source(integration_type, db=db, user=user)

    result = await db.execute(
        select(Connection).where(
            Connection.user_id == user.id,
            Connection.integration_type == integration_type,
        )
    )
    conn = result.scalar_one_or_none()

    if conn:
        conn.status = "connected"
    else:
        conn = Connection(
            user_id=user.id,
            organization_id=user.organization_id,
            integration_type=integration_type,
            status="connected",
        )
        db.add(conn)

    await db.flush()
    return {"status": "connected", "integration_type": integration_type}


@router.post("/{integration_type}/disconnect")
async def disconnect_source(
    integration_type: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Connection).where(
            Connection.user_id == user.id,
            Connection.integration_type == integration_type,
        )
    )
    conn = result.scalar_one_or_none()
    if conn:
        conn.status = "disconnected"
        conn.metadata_json = {}
        await db.flush()
    return {"status": "disconnected", "integration_type": integration_type}


@router.post("/{integration_type}/test")
async def test_connection(
    integration_type: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Actually verify the credential with a real, read-only API call."""
    try:
        if integration_type == "github":
            token = settings.GITHUB_PERSONAL_ACCESS_TOKEN
            if not token:
                result = await db.execute(
                    select(Connection).where(
                        Connection.user_id == user.id,
                        Connection.integration_type == "github",
                    )
                )
                conn = result.scalar_one_or_none()
                token = (
                    (conn.metadata_json or {}).get("access_token", "") if conn else ""
                )
            if not token:
                return {"status": "error", "message": "No GitHub credential found"}
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(
                    "https://api.github.com/user",
                    headers={"Authorization": f"Bearer {token}"},
                )
            if r.status_code == 200:
                return {
                    "status": "ok",
                    "message": f"Authenticated as {r.json().get('login')}",
                }
            return {
                "status": "error",
                "message": f"GitHub API returned HTTP {r.status_code}",
            }

        if integration_type == "slack":
            token = settings.SLACK_BOT_TOKEN
            if not token:
                result = await db.execute(
                    select(Connection).where(
                        Connection.user_id == user.id,
                        Connection.integration_type == "slack",
                    )
                )
                conn = result.scalar_one_or_none()
                token = (conn.metadata_json or {}).get("bot_token", "") if conn else ""
            if not token:
                return {"status": "error", "message": "No Slack credential found"}
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(
                    "https://slack.com/api/auth.test",
                    headers={"Authorization": f"Bearer {token}"},
                )
            data = r.json()
            if data.get("ok"):
                return {"status": "ok", "message": f"Connected to {data.get('team')}"}
            return {
                "status": "error",
                "message": f"Slack API error: {data.get('error')}",
            }

        if integration_type == "hubspot":
            token = settings.HUBSPOT_ACCESS_TOKEN
            if not token:
                result = await db.execute(
                    select(Connection).where(
                        Connection.user_id == user.id,
                        Connection.integration_type == "hubspot",
                    )
                )
                conn = result.scalar_one_or_none()
                token = (
                    (conn.metadata_json or {}).get("access_token", "") if conn else ""
                )
            if not token:
                return {"status": "error", "message": "No HubSpot credential found"}
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(
                    "https://api.hubapi.com/crm/v3/objects/contacts?limit=1",
                    headers={"Authorization": f"Bearer {token}"},
                )
            if r.status_code == 200:
                return {"status": "ok", "message": "HubSpot API responded"}
            return {
                "status": "error",
                "message": f"HubSpot API returned HTTP {r.status_code}",
            }

        if integration_type == "postgres":
            import asyncpg

            pg = await asyncpg.connect(
                settings.DATABASE_URL.replace(
                    "postgresql+asyncpg://", "postgresql://", 1
                ),
                timeout=10,
            )
            await pg.execute("SELECT 1")
            await pg.close()
            return {"status": "ok", "message": "PostgreSQL connection verified"}

        return {
            "status": "error",
            "message": f"Unsupported integration: {integration_type}",
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
