import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import User, Session, Message, RequestLog

async def get_platform_stats(db: AsyncSession) -> Dict[str, Any]:
    """Retrieve today's platform statistics and metrics."""
    start_of_today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    # 1. Total users count
    total_users_stmt = select(func.count(User.id))
    total_users = (await db.execute(total_users_stmt)).scalar() or 0

    # 2. Distinct active sessions today
    active_sessions_stmt = select(func.count(func.distinct(Message.session_id))).where(
        Message.created_at >= start_of_today
    )
    active_sessions_today = (await db.execute(active_sessions_stmt)).scalar() or 0

    # 3. Total messages sent today
    total_messages_stmt = select(func.count(Message.id)).where(
        Message.created_at >= start_of_today
    )
    total_messages_today = (await db.execute(total_messages_stmt)).scalar() or 0

    # 4. Total tokens today
    total_tokens_stmt = select(func.sum(Message.total_tokens)).where(
        Message.created_at >= start_of_today
    )
    total_tokens_today = (await db.execute(total_tokens_stmt)).scalar() or 0

    # 5. Estimated cost today in USD
    # Formula: cost = (prompt_tokens * 0.15 / 1_000_000) + (completion_tokens * 0.60 / 1_000_000)
    tokens_stmt = select(
        func.sum(Message.prompt_tokens),
        func.sum(Message.completion_tokens)
    ).where(
        Message.created_at >= start_of_today
    )
    res = (await db.execute(tokens_stmt)).one_or_none()
    prompt_tokens = 0
    completion_tokens = 0
    if res:
        prompt_tokens = res[0] or 0
        completion_tokens = res[1] or 0
    
    estimated_cost_today_usd = (prompt_tokens * 0.15 / 1_000_000) + (completion_tokens * 0.60 / 1_000_000)

    # 6. Error rate percentage today
    total_requests_stmt = select(func.count(RequestLog.id)).where(
        RequestLog.created_at >= start_of_today
    )
    total_requests = (await db.execute(total_requests_stmt)).scalar() or 0

    error_requests_stmt = select(func.count(RequestLog.id)).where(
        RequestLog.created_at >= start_of_today,
        RequestLog.status_code >= 400
    )
    error_requests = (await db.execute(error_requests_stmt)).scalar() or 0

    error_rate_percent = 0.0
    if total_requests > 0:
        error_rate_percent = (error_requests / total_requests) * 100.0

    # 7. Average response time in ms today
    avg_response_stmt = select(func.avg(RequestLog.duration_ms)).where(
        RequestLog.created_at >= start_of_today
    )
    avg_response_time_ms = (await db.execute(avg_response_stmt)).scalar() or 0.0

    return {
        "total_users": total_users,
        "active_sessions_today": active_sessions_today,
        "total_messages_today": total_messages_today,
        "total_tokens_today": total_tokens_today,
        "estimated_cost_today_usd": float(estimated_cost_today_usd),
        "error_rate_percent": float(error_rate_percent),
        "avg_response_time_ms": float(avg_response_time_ms)
    }

async def get_per_user_stats(db: AsyncSession) -> List[Dict[str, Any]]:
    """Retrieve message count, token count, and last active timestamp grouped per user."""
    stmt = (
        select(
            User.id.label("user_id"),
            User.email,
            User.full_name,
            func.count(Message.id).label("message_count"),
            func.coalesce(func.sum(Message.total_tokens), 0).label("token_count"),
            func.max(Message.created_at).label("last_active_at")
        )
        .outerjoin(Session, User.id == Session.user_id)
        .outerjoin(Message, Session.id == Message.session_id)
        .group_by(User.id, User.email, User.full_name)
        .order_by(User.created_at.desc())
    )
    result = await db.execute(stmt)
    
    stats = []
    for row in result.all():
        stats.append({
            "user_id": row.user_id,
            "email": row.email,
            "full_name": row.full_name,
            "message_count": row.message_count,
            "token_count": int(row.token_count),
            "last_active_at": row.last_active_at
        })
    return stats

async def get_token_stats(db: AsyncSession) -> Dict[str, Any]:
    """Retrieve cumulative prompt, completion, total token counts and cumulative cost."""
    stmt = select(
        func.sum(Message.prompt_tokens),
        func.sum(Message.completion_tokens),
        func.sum(Message.total_tokens)
    )
    res = (await db.execute(stmt)).one_or_none()
    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0
    if res:
        prompt_tokens = res[0] or 0
        completion_tokens = res[1] or 0
        total_tokens = res[2] or 0
        
    estimated_cost_usd = (prompt_tokens * 0.15 / 1_000_000) + (completion_tokens * 0.60 / 1_000_000)
    
    return {
        "prompt_tokens": int(prompt_tokens),
        "completion_tokens": int(completion_tokens),
        "total_tokens": int(total_tokens),
        "estimated_cost_usd": float(estimated_cost_usd)
    }

async def get_recent_logs(
    db: AsyncSession,
    endpoint: Optional[str] = None,
    status_code: Optional[int] = None,
    user_id: Optional[uuid.UUID] = None,
    limit: int = 100
) -> List[RequestLog]:
    """Retrieve filterable system request logs."""
    stmt = select(RequestLog).order_by(RequestLog.created_at.desc())
    if endpoint:
        stmt = stmt.where(RequestLog.endpoint == endpoint)
    if status_code is not None:
        stmt = stmt.where(RequestLog.status_code == status_code)
    if user_id:
        stmt = stmt.where(RequestLog.user_id == user_id)
    stmt = stmt.limit(limit)
    
    result = await db.execute(stmt)
    return list(result.scalars().all())

async def get_all_users(db: AsyncSession) -> List[User]:
    """Retrieve a list of all registered users."""
    stmt = select(User).order_by(User.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())
