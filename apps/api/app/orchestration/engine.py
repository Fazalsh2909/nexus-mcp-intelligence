from typing import AsyncGenerator, Dict, List, Any
import time
import json
from uuid import UUID

from sqlalchemy import select

from app.orchestration.llm import get_llm_provider
from app.orchestration.tools import TOOL_DEFINITIONS, execute_tool
from app.orchestration.prompts import SYSTEM_PROMPT, build_user_prompt
from app.models.models import Message

MAX_HISTORY_MESSAGES = 20
MAX_HISTORY_CHARS_PER_MESSAGE = 4000


async def _load_history(db, session_id: str) -> List[Dict[str, str]]:
    """Load prior user/assistant turns so the conversation has memory.

    The current user message is already persisted before orchestration runs,
    so the last row is the current query and is excluded (it is appended
    separately via build_user_prompt).
    """
    try:
        result = await db.execute(
            select(Message)
            .where(Message.chat_session_id == UUID(session_id))
            .order_by(Message.created_at)
        )
        rows = result.scalars().all()
    except Exception:
        return []

    history: List[Dict[str, str]] = []
    for msg in rows[-MAX_HISTORY_MESSAGES:]:
        if msg.role not in ("user", "assistant"):
            continue
        history.append(
            {
                "role": msg.role,
                "content": msg.content[:MAX_HISTORY_CHARS_PER_MESSAGE],
            }
        )
    if history:
        history = history[:-1]  # drop the current user query (re-added below)
    return history


async def orchestrate(
    query: str,
    session_id: str,
    user_id: str,
    organization_id: str,
    db,
) -> AsyncGenerator[dict, None]:
    start_time = time.time()
    llm = get_llm_provider()

    yield {"type": "thinking", "content": "Analyzing your question..."}

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]
    messages.extend(await _load_history(db, session_id))
    messages.append({"role": "user", "content": build_user_prompt(query)})

    tool_call_count = 0
    max_tool_calls = 20
    collected_tools = []
    total_input_tokens = 0
    total_output_tokens = 0

    while tool_call_count < max_tool_calls:
        response = await llm.chat_completion(messages=messages, tools=TOOL_DEFINITIONS)

        usage = response.get("usage") or {}
        total_input_tokens += int(usage.get("input_tokens") or 0)
        total_output_tokens += int(usage.get("output_tokens") or 0)

        if response.get("tool_calls"):
            messages.append(
                {
                    "role": "assistant",
                    "tool_calls": [
                        {"id": tc["id"], "type": "function", "function": tc["function"]}
                        for tc in response["tool_calls"]
                    ],
                }
            )

            for tool_call in response["tool_calls"]:
                tool_name = tool_call["function"]["name"]
                tool_args = json.loads(tool_call["function"]["arguments"])

                collected_tools.append(tool_name)
                tool_call_count += 1

                yield {
                    "type": "tool_start",
                    "tool": tool_name,
                    "description": _describe_tool_call(tool_name, tool_args),
                    "arguments": tool_args,
                }

                tool_start = time.time()
                try:
                    result = await execute_tool(
                        tool_name,
                        tool_args,
                        user_id=user_id,
                        organization_id=organization_id,
                        db=db,
                    )
                    duration_ms = (time.time() - tool_start) * 1000

                    yield {
                        "type": "tool_result",
                        "tool": tool_name,
                        "duration_ms": duration_ms,
                    }

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": json.dumps(result),
                        }
                    )
                except Exception as e:
                    yield {
                        "type": "tool_error",
                        "tool": tool_name,
                        "error": str(e),
                    }
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": json.dumps({"error": str(e)}),
                        }
                    )
        else:
            answer = response.get("content", "")
            sources = _extract_sources(collected_tools)

            for char in answer:
                yield {"type": "token", "content": char}

            if sources:
                yield {"type": "sources", "sources": sources}

            duration_ms = (time.time() - start_time) * 1000
            yield {
                "type": "usage",
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
            }
            yield {"type": "done"}
            return

    yield {
        "type": "token",
        "content": "\n\nI've gathered information from multiple sources. Here's what I found:",
    }
    yield {"type": "done"}


def _describe_tool_call(tool_name: str, args: dict) -> str:
    descriptions = {
        "slack_search_messages": f"Searching Slack for '{args.get('query', '')}'",
        "slack_get_thread": f"Fetching Slack thread in {args.get('channel', '')}",
        "slack_list_channels": "Listing Slack channels",
        "github_search_issues": f"Searching GitHub issues for '{args.get('query', '')}'",
        "github_get_issue": f"Fetching GitHub issue #{args.get('issue_number', '')}",
        "github_list_repositories": "Listing GitHub repositories",
        "github_search_code": f"Searching code for '{args.get('query', '')}'",
        "hubspot_search_contacts": f"Searching HubSpot contacts for '{args.get('name', args.get('email', ''))}'",
        "hubspot_get_contact": "Fetching HubSpot contact",
        "hubspot_search_companies": f"Searching HubSpot companies for '{args.get('name', '')}'",
        "hubspot_search_deals": "Searching HubSpot deals",
        "hubspot_get_deal": "Fetching HubSpot deal",
        "postgres_list_tables": "Listing database tables",
        "postgres_describe_table": f"Describing table '{args.get('table_name', '')}'",
        "postgres_query": "Running query on database",
        "postgres_count": f"Counting rows in '{args.get('table_name', '')}'",
    }
    return descriptions.get(tool_name, f"Calling {tool_name}")


def _extract_sources(tools_used: list) -> list:
    sources = []
    if "slack_search_messages" in tools_used or "slack_get_thread" in tools_used:
        sources.append(
            {
                "type": "slack",
                "url": "#",
                "title": "Slack messages",
                "detail": "Retrieved from Slack workspace",
            }
        )
    if any(t.startswith("github_") for t in tools_used):
        sources.append(
            {
                "type": "github",
                "url": "#",
                "title": "GitHub issues",
                "detail": "Retrieved from GitHub repositories",
            }
        )
    if any(t.startswith("hubspot_") for t in tools_used):
        sources.append(
            {
                "type": "hubspot",
                "url": "#",
                "title": "HubSpot records",
                "detail": "Retrieved from HubSpot CRM",
            }
        )
    if any(t.startswith("postgres_") for t in tools_used):
        sources.append(
            {
                "type": "database",
                "url": "#",
                "title": "Database records",
                "detail": "Retrieved from PostgreSQL database",
            }
        )
    return sources
