from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.models.models import UsageEvent, ToolCall, ChatSession, Message, User
from app.schemas.schemas import AnalyticsResponse, ToolExecutionResponse
from app.api.auth import get_current_user

router = APIRouter()


@router.get("/", response_model=AnalyticsResponse)
async def get_analytics(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
):
    org_id = user.organization_id

    total_result = await db.execute(
        select(func.count(UsageEvent.id)).where(UsageEvent.organization_id == org_id)
    )
    total_queries = total_result.scalar() or 0

    success_result = await db.execute(
        select(func.count(UsageEvent.id)).where(
            UsageEvent.organization_id == org_id,
            UsageEvent.event_type == "chat",
        )
    )
    successful_queries = success_result.scalar() or 0

    token_result = await db.execute(
        select(
            func.sum(UsageEvent.input_tokens + UsageEvent.output_tokens),
            func.sum(UsageEvent.estimated_cost),
        ).where(UsageEvent.organization_id == org_id)
    )
    row = token_result.one()
    total_tokens = row[0] or 0
    estimated_cost = float(row[1] or 0)

    tool_result = await db.execute(
        select(ToolCall.tool_name, func.count(ToolCall.id))
        .join(ToolCall.message)
        .join(Message.chat_session)
        .where(ChatSession.organization_id == org_id)
        .group_by(ToolCall.tool_name)
        .order_by(func.count(ToolCall.id).desc())
        .limit(10)
    )
    most_used = [{"tool": r[0], "count": r[1]} for r in tool_result.all()]

    investigation_result = await db.execute(
        select(func.count(ChatSession.id)).where(ChatSession.organization_id == org_id)
    )
    investigations = investigation_result.scalar() or 0

    tool_total_result = await db.execute(
        select(func.count(ToolCall.id))
        .join(ToolCall.message)
        .join(Message.chat_session)
        .where(ChatSession.organization_id == org_id)
    )
    tool_calls = tool_total_result.scalar() or 0

    tool_ok_result = await db.execute(
        select(func.count(ToolCall.id))
        .join(ToolCall.message)
        .join(Message.chat_session)
        .where(
            ChatSession.organization_id == org_id,
            ToolCall.status == "success",
        )
    )
    tool_success = tool_ok_result.scalar() or 0
    tool_success_rate = round(tool_success / tool_calls, 4) if tool_calls else None

    latency_result = await db.execute(
        select(ToolCall.duration_ms)
        .join(ToolCall.message)
        .join(Message.chat_session)
        .where(
            ChatSession.organization_id == org_id,
            ToolCall.duration_ms.isnot(None),
        )
    )
    durations = sorted(d for d in latency_result.scalars().all() if d is not None)
    median_latency = durations[len(durations) // 2] if durations else None

    recent_result = await db.execute(
        select(ToolCall)
        .join(ToolCall.message)
        .join(Message.chat_session)
        .where(ChatSession.organization_id == org_id)
        .order_by(ToolCall.created_at.desc())
        .limit(8)
    )
    recent_tool_executions = [
        ToolExecutionResponse(
            tool=tc.tool_name,
            status=tc.status,
            duration_ms=tc.duration_ms,
            created_at=tc.created_at,
        )
        for tc in recent_result.scalars().all()
    ]

    return AnalyticsResponse(
        total_queries=total_queries,
        successful_queries=successful_queries,
        failed_queries=total_queries - successful_queries,
        avg_latency_ms=median_latency or 0.0,
        avg_tool_calls_per_query=(
            round(tool_calls / total_queries, 2) if total_queries else 0.0
        ),
        total_tokens=total_tokens,
        estimated_cost=estimated_cost,
        most_used_tools=most_used,
        investigations=investigations,
        tool_calls=tool_calls,
        tool_success_rate=tool_success_rate,
        median_tool_latency_ms=median_latency,
        recent_tool_executions=recent_tool_executions,
    )
