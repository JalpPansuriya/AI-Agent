import uuid
from datetime import datetime, timedelta
from loguru import logger
from sqlalchemy import create_engine, or_, func
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.workers.celery_app import celery_app

# Set up synchronous database connection
sync_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
sync_engine = create_engine(sync_url)
SyncSessionLocal = sessionmaker(bind=sync_engine)

@celery_app.task
def log_request(request_id: str, user_id: str, endpoint: str, method: str, status_code: int, duration_ms: int, tokens_used: int, error_message: str):
    """Synchronously save a request log record into the database request_logs table."""
    from app.models.models import RequestLog
    
    uid = uuid.UUID(user_id) if user_id else None
    
    with SyncSessionLocal() as session:
        log_entry = RequestLog(
            request_id=request_id,
            user_id=uid,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            duration_ms=duration_ms,
            tokens_used=tokens_used,
            error_message=error_message
        )
        session.add(log_entry)
        session.commit()
        logger.info(f"Background task: Request logging completed for {request_id}")

@celery_app.task
def aggregate_daily_stats():
    """Daily stats aggregator calculating per-user token usage totals for yesterday and logging them."""
    from app.models.models import RequestLog
    
    yesterday = datetime.utcnow().date() - timedelta(days=1)
    start_of_yesterday = datetime.combine(yesterday, datetime.min.time())
    end_of_yesterday = datetime.combine(yesterday, datetime.max.time())
    
    with SyncSessionLocal() as session:
        query = (
            session.query(
                RequestLog.user_id,
                func.sum(RequestLog.tokens_used).label("total_tokens")
            )
            .filter(
                RequestLog.created_at >= start_of_yesterday,
                RequestLog.created_at <= end_of_yesterday,
                RequestLog.user_id.isnot(None)
            )
            .group_by(RequestLog.user_id)
        )
        rows = query.all()
        for r in rows:
            logger.info(f"Aggregated daily stats for user {r.user_id}: {r.total_tokens} tokens used on {yesterday}")

@celery_app.task
def cleanup_expired_tokens():
    """Hourly background task cleanup that hard deletes expired or revoked refresh tokens."""
    from app.models.models import RefreshToken
    
    now = datetime.utcnow()
    
    with SyncSessionLocal() as session:
        deleted = (
            session.query(RefreshToken)
            .filter(
                or_(
                    RefreshToken.is_revoked == True,
                    RefreshToken.expires_at < now
                )
            )
            .delete(synchronize_session=False)
        )
        session.commit()
        logger.info(f"Hourly background task: Cleaned up {deleted} expired or revoked refresh tokens.")
