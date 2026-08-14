from typing import Dict, Any, List
import httpx

from app.core.config import settings


async def _slack_token(db=None, user_id: str = "") -> str:
    """Resolve a Slack bot token: env override first, then the token stored
    when the workspace connected via OAuth."""
    if settings.SLACK_BOT_TOKEN:
        return settings.SLACK_BOT_TOKEN

    if db is not None and user_id:
        from sqlalchemy import select

        from app.models.models import Connection

        result = await db.execute(
            select(Connection).where(
                Connection.user_id == user_id,
                Connection.integration_type == "slack",
                Connection.status == "connected",
            )
        )
        conn = result.scalar_one_or_none()
        if conn and conn.metadata_json:
            return str(conn.metadata_json.get("bot_token") or "")
    return ""


async def _slack_call(
    token: str, method: str, payload: Dict[str, Any]
) -> Dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"https://slack.com/api/{method}", headers=headers, json=payload
        )
        data = resp.json()
        if not data.get("ok"):
            error = data.get("error", "unknown error")
            if error in ("invalid_auth", "account_inactive"):
                return {
                    "error": "Slack authentication failed. Reconnect the source in Sources."
                }
            return {"error": f"Slack API error: {error}"}
        return data


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


def _fmt_message(msg: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "ts": msg.get("ts"),
        "user": msg.get("user"),
        "text": (msg.get("text") or "")[:1000],
        "channel": msg.get("channel"),
        "permalink": msg.get("permalink"),
        "created_at": msg.get("ts"),
    }


def _ts_from_date(date_str: str, end_of_day: bool = False) -> float:
    """Convert YYYY-MM-DD to a Slack timestamp (seconds)."""
    import datetime

    try:
        d = datetime.date.fromisoformat(date_str)
    except ValueError:
        return 0.0
    if end_of_day:
        dt = datetime.datetime(d.year, d.month, d.day, 23, 59, 59)
    else:
        dt = datetime.datetime(d.year, d.month, d.day)
    return dt.timestamp()


async def execute_slack_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    user_id: str = "",
    organization_id: str = "",
    db=None,
) -> Dict[str, Any]:
    token = await _slack_token(db=db, user_id=user_id)
    if not token:
        return {
            "error": (
                "Slack is not connected. Click Connect on the Sources page to "
                "authorize the app, or set SLACK_BOT_TOKEN in .env."
            )
        }

    try:
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
            return {
                "channel": channel,
                "messages": [_fmt_message(m) for m in data.get("messages", [])],
                "total": len(data.get("messages", [])),
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
            return {
                "channel": channel,
                "thread": [_fmt_message(m) for m in data.get("messages", [])],
                "total": len(data.get("messages", [])),
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
                    match = _fmt_message(m)
                    match["channel"] = channel["name"]
                    matches.append(match)

            return {"messages": matches, "total": len(matches)}

        return {"error": f"Unknown Slack tool: {tool_name}"}
    except httpx.HTTPError as e:
        return {"error": f"Slack request failed: {str(e)}"}


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
