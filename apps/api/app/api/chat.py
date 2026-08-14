from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from uuid import UUID
from datetime import datetime
import json

from app.core.config import settings
from app.db.session import get_db
from app.models.models import (
    ChatSession,
    Message,
    ToolCall,
    UsageEvent,
    User,
)
from app.schemas.schemas import (
    ChatSessionCreate,
    ChatSessionUpdate,
    ChatSessionResponse,
    MessageCreate,
    ChatSessionWithMessages,
    SessionSummaryResponse,
    ToolActivity,
)
from app.api.auth import get_current_user
from app.orchestration.engine import (
    orchestrate,
    confirm_action,
    reject_action,
    arguments_hash,
)

router = APIRouter()


@router.get("/sessions", response_model=list[SessionSummaryResponse])
async def list_sessions(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == user.id)
        .order_by(ChatSession.updated_at.desc())
    )
    sessions = result.scalars().all()
    if not sessions:
        return []

    session_ids = [s.id for s in sessions]

    msgs_result = await db.execute(
        select(Message)
        .where(Message.chat_session_id.in_(session_ids))
        .order_by(Message.created_at)
    )
    msgs_by_session: dict[UUID, list[Message]] = {}
    session_by_message: dict[UUID, UUID] = {}
    for m in msgs_result.scalars().all():
        msgs_by_session.setdefault(m.chat_session_id, []).append(m)
        session_by_message[m.id] = m.chat_session_id

    tools_result = await db.execute(
        select(ToolCall.message_id, ToolCall.tool_name).where(
            ToolCall.message_id.in_(session_by_message.keys())
        )
    )
    tools_by_session: dict[UUID, dict[str, int]] = {}
    for message_id, tool_name in tools_result.all():
        session_id = session_by_message.get(message_id)
        if session_id:
            counts = tools_by_session.setdefault(session_id, {})
            counts[tool_name] = counts.get(tool_name, 0) + 1

    def _truncate(text: str, limit: int) -> str:
        text = text.strip()
        if len(text) <= limit:
            return text
        return text[: limit - 1] + "…"

    summaries = []
    for s in sessions:
        msgs = msgs_by_session.get(s.id, [])
        last_user = next(
            (m for m in reversed(msgs) if m.role == "user" and m.content.strip()),
            None,
        )
        last_assistant = next(
            (m for m in reversed(msgs) if m.role == "assistant" and m.content.strip()),
            None,
        )
        tool_counts = tools_by_session.get(s.id, {})
        summaries.append(
            SessionSummaryResponse(
                id=s.id,
                title=s.title,
                created_at=s.created_at,
                message_count=len(msgs),
                question=(_truncate(last_user.content, 140) if last_user else None),
                tools=[
                    {"tool": t, "count": c}
                    for t, c in sorted(tool_counts.items(), key=lambda kv: -kv[1])
                ],
                result=(
                    _truncate(last_assistant.content, 160) if last_assistant else None
                ),
            )
        )
    return summaries


@router.post("/sessions", response_model=ChatSessionResponse)
async def create_session(
    data: ChatSessionCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session = ChatSession(
        user_id=user.id,
        organization_id=user.organization_id,
        title=data.title or "New conversation",
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return session


@router.get("/sessions/{session_id}", response_model=ChatSessionWithMessages)
async def get_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ChatSession)
        .options(selectinload(ChatSession.messages).selectinload(Message.tool_calls))
        .where(ChatSession.id == session_id, ChatSession.user_id == user.id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return session


@router.patch("/sessions/{session_id}", response_model=ChatSessionResponse)
async def rename_session(
    session_id: UUID,
    data: ChatSessionUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id, ChatSession.user_id == user.id
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.title = data.title.strip() or "New conversation"
    await db.flush()
    await db.refresh(session)
    return session


@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: UUID,
    data: MessageCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id, ChatSession.user_id == user.id
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    user_msg = Message(
        chat_session_id=session.id,
        role="user",
        content=data.content,
    )
    db.add(user_msg)
    session.updated_at = datetime.utcnow()
    await db.flush()
    # Commit now: if the client disconnects mid-stream, the request teardown
    # never commits, so anything persisted must be committed in-flight.
    await db.commit()

    async def event_stream():
        full_response = ""
        tool_activities = []
        tool_call_objects = []
        total_input_tokens = 0
        total_output_tokens = 0
        last_flushed = 0
        completed = False

        # Persist the assistant message immediately so history is never lost,
        # even if the client disconnects mid-stream.
        assistant_msg = Message(
            chat_session_id=session.id,
            role="assistant",
            content="",
        )
        db.add(assistant_msg)
        await db.flush()
        await db.commit()

        try:
            async for event in orchestrate(
                query=data.content,
                session_id=str(session.id),
                user_id=str(user.id),
                organization_id=str(user.organization_id),
                db=db,
            ):
                if event["type"] == "thinking":
                    yield f"data: {json.dumps({'type': 'thinking', 'content': event['content']})}\n\n"
                elif event["type"] == "tool_start":
                    activity = ToolActivity(
                        tool=event["tool"],
                        status="running",
                        description=event.get(
                            "description", f"Calling {event['tool']}"
                        ),
                    )
                    tool_activities.append(activity)
                    tool_call = ToolCall(
                        message_id=assistant_msg.id,
                        tool_name=event["tool"],
                        arguments_json=event.get("arguments", {}),
                        arguments_hash=arguments_hash(event.get("arguments", {})),
                        status="running",
                    )
                    tool_call_objects.append(tool_call)
                    db.add(tool_call)
                    yield f"data: {json.dumps({'type': 'tool_start', 'tool': event['tool'], 'description': event.get('description', '')})}\n\n"
                elif event["type"] == "tool_result":
                    for act, tc in zip(tool_activities, tool_call_objects):
                        if act.tool == event["tool"] and act.status == "running":
                            act.status = "success"
                            act.duration_ms = event.get("duration_ms")
                            tc.status = "success"
                            tc.duration_ms = event.get("duration_ms")
                    assistant_msg.content = full_response
                    await db.flush()
                    await db.commit()
                    last_flushed = len(full_response)
                    yield f"data: {json.dumps({'type': 'tool_result', 'tool': event['tool'], 'duration_ms': event.get('duration_ms', 0)})}\n\n"
                elif event["type"] == "tool_error":
                    for act, tc in zip(tool_activities, tool_call_objects):
                        if act.tool == event["tool"] and act.status == "running":
                            act.status = "error"
                            tc.status = "error"
                            tc.error_message = event.get("error")
                    assistant_msg.content = full_response
                    await db.flush()
                    await db.commit()
                    last_flushed = len(full_response)
                    yield f"data: {json.dumps({'type': 'tool_error', 'tool': event['tool'], 'error': event.get('error', '')})}\n\n"
                elif event["type"] == "token":
                    full_response += event["content"]
                    assistant_msg.content = full_response
                    # Commit incrementally so a disconnect (page switch, reload)
                    # never loses more than the last ~128 characters of the answer.
                    if len(full_response) - last_flushed > 128:
                        await db.flush()
                        await db.commit()
                        last_flushed = len(full_response)
                    yield f"data: {json.dumps({'type': 'token', 'content': event['content']})}\n\n"
                elif event["type"] == "confirmation_request":
                    yield f"data: {json.dumps({'type': 'confirmation_request', 'action_id': event['action_id'], 'tool': event['tool'], 'description': event['description'], 'arguments': event['arguments']})}\n\n"
                elif event["type"] == "sources":
                    yield f"data: {json.dumps({'type': 'sources', 'sources': event['sources']})}\n\n"
                elif event["type"] == "usage":
                    total_input_tokens = int(event.get("input_tokens") or 0)
                    total_output_tokens = int(event.get("output_tokens") or 0)
                elif event["type"] == "error":
                    yield f"data: {json.dumps({'type': 'error', 'content': event['content']})}\n\n"
                elif event["type"] == "done":
                    completed = True
                    break
        except Exception:
            import logging

            logging.getLogger(__name__).exception("Chat stream error")
            yield f"data: {json.dumps({'type': 'error', 'content': 'An internal error occurred. Please try again.'})}\n\n"
        finally:
            # Persist whatever was generated even if the client disconnected.
            try:
                assistant_msg.content = full_response
                assistant_msg.sources_json = (
                    [a.model_dump() for a in tool_activities]
                    if tool_activities
                    else None
                )
                session.updated_at = datetime.utcnow()
                db.add(
                    UsageEvent(
                        user_id=user.id,
                        organization_id=user.organization_id,
                        event_type="chat" if completed else "error",
                        model=settings.LLM_MODEL,
                        input_tokens=total_input_tokens,
                        output_tokens=total_output_tokens,
                    )
                )
                await db.flush()
                await db.commit()
            except BaseException:
                pass

        if completed:
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/sessions/{session_id}/actions/{action_id}/confirm")
async def confirm_action_endpoint(
    session_id: UUID,
    action_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id, ChatSession.user_id == user.id
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    async def event_stream():
        tool_activities = []
        tool_call_objects = []
        total_input_tokens = 0
        total_output_tokens = 0
        completed = False

        assistant_msg = Message(
            chat_session_id=session.id,
            role="assistant",
            content="",
        )
        db.add(assistant_msg)
        await db.flush()
        await db.commit()

        try:
            async for event in confirm_action(
                action_id=str(action_id),
                session_id=str(session.id),
                user_id=str(user.id),
                organization_id=str(user.organization_id),
                db=db,
            ):
                if event["type"] == "thinking":
                    yield f"data: {json.dumps({'type': 'thinking', 'content': event['content']})}\n\n"
                elif event["type"] == "tool_start":
                    tool_activities.append(event)
                    tool_call = ToolCall(
                        message_id=assistant_msg.id,
                        tool_name=event["tool"],
                        arguments_json=event.get("arguments", {}),
                        arguments_hash=arguments_hash(event.get("arguments", {})),
                        status="running",
                    )
                    tool_call_objects.append(tool_call)
                    db.add(tool_call)
                    yield f"data: {json.dumps({'type': 'tool_start', 'tool': event['tool'], 'description': event.get('description', '')})}\n\n"
                elif event["type"] == "tool_result":
                    for tc in tool_call_objects:
                        if tc.tool_name == event["tool"] and tc.status == "running":
                            tc.status = "success"
                            tc.duration_ms = event.get("duration_ms")
                    yield f"data: {json.dumps({'type': 'tool_result', 'tool': event['tool'], 'duration_ms': event.get('duration_ms', 0)})}\n\n"
                elif event["type"] == "tool_error":
                    for tc in tool_call_objects:
                        if tc.tool_name == event["tool"] and tc.status == "running":
                            tc.status = "error"
                            tc.error_message = event.get("error")
                    yield f"data: {json.dumps({'type': 'tool_error', 'tool': event['tool'], 'error': event.get('error', '')})}\n\n"
                elif event["type"] == "token":
                    assistant_msg.content += event["content"]
                    yield f"data: {json.dumps({'type': 'token', 'content': event['content']})}\n\n"
                elif event["type"] == "sources":
                    yield f"data: {json.dumps({'type': 'sources', 'sources': event['sources']})}\n\n"
                elif event["type"] == "usage":
                    total_input_tokens = int(event.get("input_tokens") or 0)
                    total_output_tokens = int(event.get("output_tokens") or 0)
                elif event["type"] == "error":
                    yield f"data: {json.dumps({'type': 'error', 'content': event['content']})}\n\n"
                elif event["type"] == "done":
                    completed = True
                    break
        except Exception:
            import logging

            logging.getLogger(__name__).exception("Confirm stream error")
            yield f"data: {json.dumps({'type': 'error', 'content': 'An internal error occurred. Please try again.'})}\n\n"
        finally:
            try:
                assistant_msg.sources_json = (
                    [a for a in tool_activities] if tool_activities else None
                )
                session.updated_at = datetime.utcnow()
                db.add(
                    UsageEvent(
                        user_id=user.id,
                        organization_id=user.organization_id,
                        event_type="chat" if completed else "error",
                        model=settings.LLM_MODEL,
                        input_tokens=total_input_tokens,
                        output_tokens=total_output_tokens,
                    )
                )
                await db.flush()
                await db.commit()
            except BaseException:
                pass

        if completed:
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/sessions/{session_id}/actions/{action_id}/cancel")
async def cancel_action_endpoint(
    session_id: UUID,
    action_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id, ChatSession.user_id == user.id
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    cancelled = await reject_action(str(action_id), str(session.id), str(user.id), db)
    if not cancelled:
        raise HTTPException(status_code=409, detail="Action already handled")
    return {"status": "rejected", "action_id": str(action_id)}
