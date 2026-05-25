import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_admin
from app.schemas.admin import PlatformStatsResponse, UserStatsResponse, TokenStatsResponse, LogResponse
from app.schemas.auth import UserResponse
from app.services import analytics_service

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(get_current_admin)])

@router.get(
    "/analytics",
    response_model=PlatformStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get platform statistics"
)
async def get_platform_analytics(db: AsyncSession = Depends(get_db)):
    """Retrieve platform usage statistics including user count, active sessions, and estimated cost."""
    return await analytics_service.get_platform_stats(db)


@router.get(
    "/analytics/users",
    response_model=List[UserStatsResponse],
    status_code=status.HTTP_200_OK,
    summary="Get user-specific metrics"
)
async def get_user_analytics(db: AsyncSession = Depends(get_db)):
    """Retrieve message and token count per user, along with their last active timestamp."""
    return await analytics_service.get_per_user_stats(db)


@router.get(
    "/analytics/tokens",
    response_model=TokenStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get token statistics and cumulative cost"
)
async def get_token_analytics(db: AsyncSession = Depends(get_db)):
    """Retrieve token counts and cumulative cost calculated from LLM responses."""
    return await analytics_service.get_token_stats(db)


@router.get(
    "/logs",
    response_model=List[LogResponse],
    status_code=status.HTTP_200_OK,
    summary="Get filterable request logs"
)
async def get_logs(
    endpoint: Optional[str] = Query(None, description="Filter logs by endpoint"),
    status_code: Optional[int] = Query(None, description="Filter logs by status code"),
    user_id: Optional[uuid.UUID] = Query(None, description="Filter logs by user UUID"),
    limit: int = Query(100, ge=1, le=1000, description="Max logs to return"),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve recent API request logs filterable by endpoint, status code, and user."""
    return await analytics_service.get_recent_logs(
        db, endpoint=endpoint, status_code=status_code, user_id=user_id, limit=limit
    )


@router.get(
    "/users",
    response_model=List[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="Get all users"
)
async def get_users(db: AsyncSession = Depends(get_db)):
    """Retrieve a list of all registered users. Excludes hashed passwords."""
    return await analytics_service.get_all_users(db)
