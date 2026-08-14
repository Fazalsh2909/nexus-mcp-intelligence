from typing import Dict, Any, List
import datetime
import httpx

from app.orchestration.credentials import resolve_slack_tokens
from app.orchestration.http import call_with_retry, friendly_error

_SLACK_API = "https://slack.com/api"

# Cached workspace domain (from team.info) used to build message permalinks.
_workspace_domain: str = ""


def _ts_from_date(date_str: str, end_of_day: bool = False) -> float:
    """Convert YYYY-MM-DD to a Slack timestamp (seconds)."""
    try:
        d = datetime.date.fromisoformat(date_str)
    except ValueError:
        return 0.0
    if end_of_day:
        dt = datetime.datetime(d.year, d.month, d.day, 23, 59, 59)
    else:
        dt = datetime.datetime(d.year, d.month, d.day)
    return dt.timestamp()


def _permalink(channel: str, ts: str) -> str:
    """Build a real Slack permalink: https://<workspace>.slack.com/archives/<channel>/p<ts>"""
    digits = ts.replace(".", "")
    return f"https://{_workspace_domain}.slack.com/archives/{channel}/p{digits}"


async def _team_domain(token: str) -> str:
    """Fetch and cache the workspace domain via team.info (team:read scope)."""
    global _workspace_domain
    if _workspace_domain:
        return _workspace_domain
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await call_with_retry(
                client,
                "POST",
                f"{_SLACK_API}/team.info",
                headers={"Authorization": f"Bearer {token}"},
                friendly_name="Slack",
            )
            data = resp.json()
        if data.get("ok"):
            _workspace_domain = (data.get("team") or {}).get("domain", "")
    except httpx.HTTPError:
        pass
    return _workspace_domain


async def _slack_call(
    token: str, method: str, payload: Dict[str, Any]
) -> Dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await call_with_retry(
                client,
                "POST",
                f"{_SLACK_API}/{method}",
                headers=headers,
                json=payload,
                friendly_name="Slack",
            )
        data = resp.json()
        if not data.get("ok"):
            error = data.get("error", "unknown error")
            if error in ("invalid_auth", "account_inactive"):
                return {
                    "error": "Slack authentication failed. Reconnect the source in Sources."
                }
            if error == "missing_scope":
                return {
                    "error": (
                        "The Slack app is missing a required permission for this "
                        "operation. Reinstall the app with the requested scopes."
                    )
                }
            if error == "ratelimited":
                return {
                    "error": "Slack is rate-limiting requests right now. Wait a moment and try again."
                }
            return {"error": f"Slack API error: {error}"}
        return data
    except httpx.HTTPError as e:
        return friendly_error("Slack", e, context="request")


async def _resolve_channel(token: str, channel: str) -> str:
    """Translate a #name to a channel ID when needed."""
    if channel.startswith("C") and channel.isalnum() and len(channel) == 9:
        return channel
    data = await _slack_call(
        token,
        "conversations.list",
        {"types": "public_channel,private_channel", "limit": 200},
    )
    for ch in data.get("channels", []):
        if ch["name"] == channel.lstrip("#"):
            return ch["id"]
    return channel


def _fmt_message(msg: Dict[str, Any], channel: str, token: str) -> Dict[str, Any]:
    ts = msg.get("ts")
    return {
        "ts": ts,
        "user": msg.get("user"),
        "text": (msg.get("text") or "")[:1000],
        "channel": channel,
        "permalink": _permalink(channel, str(ts)) if ts else "",
        "created_at": ts,
    }


async def execute_slack_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    user_id: str = "",
    organization_id: str = "",
    db=None,
) -> Dict[str, Any]:
    tokens = await resolve_slack_tokens(db, user_id)
    token = tokens.get("bot_token") or tokens.get("access_token")
    if not token:
        return {
            "error": (
                "Slack is not connected. Click Connect on the Sources page to "
                "authorize the app, or set SLACK_BOT_TOKEN in .env."
            )
        }

    await _team_domain(token)

    if tool_name == "slack_list_channels":
        limit = min(int(arguments.get("limit", 50)), 200)
        data = await _slack_call(
            token,
            "conversations.list",
            {"types": "public_channel,private_channel", "limit": limit},
        )
        if data.get("error"):
            return data
        return {
            "channels": [
                {
                    "id": c["id"],
                    "name": c["name"],
                    "is_private": c.get("is_private", False),
                    "num_members": c.get("num_members", 0),
                }
                for c in data.get("channels", [])
            ],
            "total": len(data.get("channels", [])),
            "evidence": [
                {
                    "source": "slack",
                    "type": "channel",
                    "id": c["id"],
                    "title": f"#{c['name']}",
                    "url": f"https://{_workspace_domain}.slack.com/app_redirect?channel={c['id']}"
                    if _workspace_domain
                    else "",
                    "timestamp": None,
                    "content": "",
                }
                for c in data.get("channels", [])[:5]
            ],
        }

    elif tool_name == "slack_get_channel_history":
        channel = arguments.get("channel", "")
        if not channel:
            return {"error": "channel is required"}
        channel_id = await _resolve_channel(token, channel)
        limit = min(int(arguments.get("limit", 20)), 100)
        data = await _slack_call(
            token, "conversations.history", {"channel": channel_id, "limit": limit}
        )
        if data.get("error"):
            return data
        msgs = data.get("messages", [])
        return {
            "channel": channel,
            "messages": [_fmt_message(m, channel_id, token) for m in msgs],
            "total": len(msgs),
            "evidence": [
                {
                    "source": "slack",
                    "type": "message",
                    "id": m.get("ts", ""),
                    "channel": channel,
                    "title": f"#{channel}",
                    "url": _permalink(channel_id, str(m.get("ts", ""))),
                    "timestamp": m.get("ts"),
                    "content": (m.get("text") or "")[:1000],
                }
                for m in msgs[:5]
            ],
        }

    elif tool_name == "slack_get_thread":
        channel = arguments.get("channel", "")
        ts = arguments.get("message_ts", "")
        if not channel or not ts:
            return {"error": "channel and message_ts are required"}
        channel_id = await _resolve_channel(token, channel)
        data = await _slack_call(
            token, "conversations.replies", {"channel": channel_id, "ts": ts}
        )
        if data.get("error"):
            return data
        msgs = data.get("messages", [])
        return {
            "channel": channel,
            "thread": [_fmt_message(m, channel_id, token) for m in msgs],
            "total": len(msgs),
            "evidence": [
                {
                    "source": "slack",
                    "type": "message",
                    "id": m.get("ts", ""),
                    "channel": channel,
                    "title": f"Thread in #{channel}",
                    "url": _permalink(channel_id, str(m.get("ts", ""))),
                    "timestamp": m.get("ts"),
                    "content": (m.get("text") or "")[:1000],
                }
                for m in msgs[:5]
            ],
        }

    elif tool_name == "slack_search_messages":
        query = arguments.get("query", "")
        if not query:
            return {"error": "query is required"}
        limit = min(int(arguments.get("limit", 10)), 50)
        per_channel = min(int(arguments.get("per_channel", 50)), 200)

        date_from = arguments.get("date_from")
        date_to = arguments.get("date_to")
        ts_min = _ts_from_date(date_from) if date_from else None
        ts_max = _ts_from_date(date_to, end_of_day=True) if date_to else None

        channels_to_scan: List[Dict[str, Any]] = []
        requested = arguments.get("channel")
        if requested:
            channel_id = await _resolve_channel(token, requested)
            channels_to_scan = [{"id": channel_id, "name": requested.lstrip("#")}]
        else:
            data = await _slack_call(
                token,
                "conversations.list",
                {"types": "public_channel,private_channel", "limit": 200},
            )
            if data.get("error"):
                return data
            channels_to_scan = [
                {
                    "id": c["id"],
                    "name": c["name"],
                    "is_private": c.get("is_private", False),
                }
                for c in data.get("channels", [])
                if not c.get("is_archived", False)
            ]

        matches: List[Dict[str, Any]] = []
        for channel in channels_to_scan:
            if len(matches) >= limit:
                break
            if not channel.get("is_member", True) and not channel.get(
                "is_private", False
            ):
                await _slack_call(
                    token, "conversations.join", {"channel": channel["id"]}
                )
            data = await _slack_call(
                token,
                "conversations.history",
                {"channel": channel["id"], "limit": per_channel},
            )
            if data.get("error"):
                continue
            q = query.lower()
            for m in data.get("messages", []):
                if len(matches) >= limit:
                    break
                text = m.get("text") or ""
                if q not in text.lower():
                    continue
                ts = float(m.get("ts", 0))
                if ts_min is not None and ts < ts_min:
                    continue
                if ts_max is not None and ts > ts_max:
                    continue
                match = _fmt_message(m, channel["id"], token)
                match["channel"] = channel["name"]
                matches.append(match)

        return {
            "messages": matches,
            "total": len(matches),
            "evidence": [
                {
                    "source": "slack",
                    "type": "message",
                    "id": m.get("ts", ""),
                    "channel": m.get("channel", ""),
                    "title": f"#{m.get('channel', '')}",
                    "url": m.get("permalink", ""),
                    "timestamp": m.get("ts"),
                    "content": m.get("text", ""),
                }
                for m in matches[:5]
            ],
        }

    return {"error": f"Unknown Slack tool: {tool_name}"}


slack_tools: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "slack_search_messages",
            "description": "Search recent messages in Slack channels the bot can access (scans the latest messages in each channel). Returns matching messages with metadata.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "channel": {
                        "type": "string",
                        "description": "Optional channel name to scope search",
                    },
                    "date_from": {
                        "type": "string",
                        "description": "Start date (YYYY-MM-DD)",
                    },
                    "date_to": {
                        "type": "string",
                        "description": "End date (YYYY-MM-DD)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results",
                        "default": 10,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "slack_get_thread",
            "description": "Get all messages in a Slack thread",
            "parameters": {
                "type": "object",
                "properties": {
                    "channel": {"type": "string", "description": "Channel ID or name"},
                    "message_ts": {
                        "type": "string",
                        "description": "Thread parent message timestamp",
                    },
                },
                "required": ["channel", "message_ts"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "slack_list_channels",
            "description": "List available Slack channels",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Max channels to return",
                        "default": 50,
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "slack_get_channel_history",
            "description": "Get recent messages from a Slack channel",
            "parameters": {
                "type": "object",
                "properties": {
                    "channel": {"type": "string", "description": "Channel ID or name"},
                    "limit": {
                        "type": "integer",
                        "description": "Max messages",
                        "default": 20,
                    },
                },
                "required": ["channel"],
            },
        },
    },
]
