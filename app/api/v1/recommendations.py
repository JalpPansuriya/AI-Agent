import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, RateLimiter
from app.models.models import User, Session
from app.schemas.product import ProductResponse
from app.services import recommendation_service
from app.repositories import session_repo

router = APIRouter(tags=["recommendations"])

@router.get(
    "/recommendations",
    response_model=List[ProductResponse],
    status_code=status.HTTP_200_OK,
    summary="Get recommendations from the most recent session",
    description="Retrieves product recommendations using the user's most recently updated chat session."
)
async def get_recent_recommendations(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rate_limit: None = Depends(RateLimiter(limit=10, group="recommendations"))
):
    # Find the most recently updated session
    from sqlalchemy import select
    result = await db.execute(
        select(Session)
        .where(Session.user_id == current_user.id)
        .order_by(Session.updated_at.desc())
        .limit(1)
    )
    session = result.scalar_one_or_none()
    if not session:
        # Fallback if no sessions exist
        from app.repositories import product_repo
        return await product_repo.get_recent_products(db, limit=5)
        
    return await recommendation_service.get_recommendations(db, session_id=session.id, user_id=current_user.id)


@router.get(
    "/recommendations/{session_id}",
    response_model=List[ProductResponse],
    status_code=status.HTTP_200_OK,
    summary="Get recommendations for a specific session",
    description="Retrieves product recommendations based on a specific chat session's conversation history."
)
async def get_session_recommendations(
    session_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rate_limit: None = Depends(RateLimiter(limit=10, group="recommendations"))
):
    session = await session_repo.get_session_by_id(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    if session.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden to this session"
        )
        
    return await recommendation_service.get_recommendations(db, session_id=session.id, user_id=current_user.id)
