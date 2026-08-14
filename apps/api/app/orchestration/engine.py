from typing import AsyncGenerator, Dict, List, Any
import time
import json
import hashlib
from datetime import datetime
from uuid import UUID

from sqlalchemy import select

from app.orchestration.llm import get_llm_provider
from app.orchestration.tools import TOOL_DEFINITIONS, execute_tool, WRITE_TOOLS
from app.orchestration.prompts import SYSTEM_PROMPT, build_user_prompt
from app.models.models import Message, PendingAction

MAX_HISTORY_MESSAGES = 20
MAX_HISTORY_CHARS_PER_MESSAGE = 4000
MAX_SOURCES = 5


def arguments_hash(arguments: Dict[str, Any]) -> str:
    """Deterministic SHA-256 of the tool arguments for auditability."""
    canonical = json.dumps(arguments, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


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
    evidence_list: List[Dict[str, Any]] = []
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

                # Write tools never execute without explicit human confirmation.
                if tool_name in WRITE_TOOLS:
                    action = PendingAction(
                        session_id=UUID(session_id),
                        user_id=UUID(user_id),
                        tool_name=tool_name,
                        arguments_json=tool_args,
                        status="pending",
                    )
                    db.add(action)
                    await db.flush()
                    await db.commit()
                    yield {
                        "type": "confirmation_request",
                        "action_id": str(action.id),
                        "tool": tool_name,
                        "description": _describe_tool_call(tool_name, tool_args),
                        "arguments": tool_args,
                    }
                    yield {"type": "done"}
                    return

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

                    evidence = result.get("evidence")
                    if isinstance(evidence, list):
                        evidence_list.extend(evidence)

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
            sources = _build_sources(evidence_list, collected_tools)

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
        "slack_get_channel_history": f"Fetching Slack history in {args.get('channel', '')}",
        "github_search_issues": f"Searching GitHub issues for '{args.get('query', '')}'",
        "github_get_issue": f"Fetching GitHub issue #{args.get('issue_number', '')}",
        "github_get_issue_comments": f"Fetching comments on issue #{args.get('issue_number', '')}",
        "github_list_repositories": "Listing GitHub repositories",
        "github_search_code": f"Searching code for '{args.get('query', '')}'",
        "github_create_issue": f"Creating GitHub issue '{args.get('title', '')}' in {args.get('repository', '')}",
        "hubspot_search_contacts": f"Searching HubSpot contacts for '{args.get('name', args.get('email', ''))}'",
        "hubspot_get_contact": "Fetching HubSpot contact",
        "hubspot_search_companies": f"Searching HubSpot companies for '{args.get('name', '')}'",
        "hubspot_get_company": "Fetching HubSpot company",
        "hubspot_search_deals": "Searching HubSpot deals",
        "hubspot_get_deal": "Fetching HubSpot deal",
        "hubspot_add_contact_note": f"Adding note to HubSpot contact {args.get('contact_id', '')}",
        "postgres_list_tables": "Listing database tables",
        "postgres_describe_table": f"Describing table '{args.get('table_name', '')}'",
        "postgres_query": "Running query on database",
        "postgres_count": f"Counting rows in '{args.get('table_name', '')}'",
    }
    return descriptions.get(tool_name, f"Calling {tool_name}")


def _build_sources(evidence_list: List[Dict[str, Any]], tools_used: list) -> list:
    """Prefer real evidence objects from tool results; fall back to tool-level
    placeholders when a provider returned no evidence."""
    if evidence_list:
        sources = []
        seen = set()
        for e in evidence_list:
            key = (e.get("source"), e.get("url"), e.get("id"))
            if key in seen:
                continue
            seen.add(key)
            sources.append(
                {
                    "type": e.get("source", "web"),
                    "url": e.get("url") or "",
                    "title": e.get("title") or "",
                    "detail": (e.get("content") or "")[:200],
                }
            )
            if len(sources) >= MAX_SOURCES:
                break
        return sources
    return _extract_sources(tools_used)


async def confirm_action(
    action_id: str,
    session_id: str,
    user_id: str,
    organization_id: str,
    db,
) -> AsyncGenerator[dict, None]:
    """Execute a confirmed write action, then summarize the outcome with the LLM."""
    result = await db.execute(
        select(PendingAction).where(
            PendingAction.id == UUID(action_id),
            PendingAction.session_id == UUID(session_id),
            PendingAction.user_id == UUID(user_id),
        )
    )
    action = result.scalar_one_or_none()
    if action is None or action.status != "pending":
        yield {
            "type": "error",
            "content": "This action is no longer available. It may have already been handled or expired.",
        }
        yield {"type": "done"}
        return

    action.status = "confirmed"
    action.responded_at = datetime.utcnow()
    await db.flush()
    await db.commit()

    yield {"type": "thinking", "content": f"Performing {action.tool_name}..."}

    tool_args = dict(action.arguments_json or {})
    yield {
        "type": "tool_start",
        "tool": action.tool_name,
        "description": _describe_tool_call(action.tool_name, tool_args),
        "arguments": tool_args,
    }

    tool_start = time.time()
    result = await execute_tool(
        action.tool_name,
        tool_args,
        user_id=user_id,
        organization_id=organization_id,
        db=db,
    )
    duration_ms = (time.time() - tool_start) * 1000

    evidence_list = result.get("evidence") if isinstance(result, dict) else []
    if "error" in (result or {}):
        action.status = "failed"
        await db.flush()
        await db.commit()
        yield {
            "type": "tool_error",
            "tool": action.tool_name,
            "error": result["error"],
        }
        yield {"type": "error", "content": result["error"]}
        yield {"type": "done"}
        return

    action.status = "executed"
    await db.flush()
    await db.commit()
    yield {"type": "tool_result", "tool": action.tool_name, "duration_ms": duration_ms}

    llm = get_llm_provider()
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "The user confirmed the action below and it has been completed.\n\n"
                f"Tool: {action.tool_name}\n"
                f"Arguments: {json.dumps(tool_args, default=str)}\n"
                f"Result: {json.dumps(result, default=str)[:4000]}\n\n"
                "Tell the user what was done and its outcome, in a short natural "
                "message (2-4 sentences)."
            ),
        },
    ]
    try:
        response = await llm.chat_completion(messages=messages, tools=[])
        answer = response.get("content", "")
        usage = response.get("usage") or {}
    except Exception:
        # The action itself already completed; summarize factually without
        # the LLM rather than failing the whole confirmation stream.
        answer = (
            f"The {action.tool_name} action was completed successfully."
            f"\n\nResult: {json.dumps(result, default=str)[:2000]}"
        )
        usage = {}

    for char in answer:
        yield {"type": "token", "content": char}

    if evidence_list:
        yield {
            "type": "sources",
            "sources": _build_sources(evidence_list, [action.tool_name]),
        }
    yield {
        "type": "usage",
        "input_tokens": int(usage.get("input_tokens") or 0),
        "output_tokens": int(usage.get("output_tokens") or 0),
    }
    yield {"type": "done"}


async def reject_action(action_id: str, session_id: str, user_id: str, db) -> bool:
    """Mark a pending action as rejected by the user."""
    result = await db.execute(
        select(PendingAction).where(
            PendingAction.id == UUID(action_id),
            PendingAction.session_id == UUID(session_id),
            PendingAction.user_id == UUID(user_id),
        )
    )
    action = result.scalar_one_or_none()
    if action is None or action.status != "pending":
        return False
    action.status = "rejected"
    action.responded_at = datetime.utcnow()
    await db.flush()
    await db.commit()
    return True


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
