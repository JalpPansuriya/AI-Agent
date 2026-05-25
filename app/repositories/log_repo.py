import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import RequestLog

async def create_request_log(
    db: AsyncSession,
    request_id: str,
    user_id: Optional[uuid.UUID],
    endpoint: str,
    method: str,
    status_code: int,
    duration_ms: int,
    tokens_used: int,
    error_message: Optional[str] = None
) -> RequestLog:
    """Save request details to the request_logs table."""
    log_entry = RequestLog(
        request_id=request_id,
        user_id=user_id,
        endpoint=endpoint,
        method=method,
        status_code=status_code,
        duration_ms=duration_ms,
        tokens_used=tokens_used,
        error_message=error_message
    )
    db.add(log_entry)
    await db.commit()
    await db.refresh(log_entry)
    return log_entry
