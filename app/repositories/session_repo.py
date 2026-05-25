import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import Session

async def create_session(
    db: AsyncSession, user_id: uuid.UUID, title: Optional[str] = None
) -> Session:
    """Create a new chat session for a user. Generates default title if none provided."""
    session_title = title if title and title.strip() else "New Chat"
    session = Session(
        user_id=user_id,
        title=session_title,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session

async def get_sessions_by_user(db: AsyncSession, user_id: uuid.UUID) -> List[Session]:
    """Retrieve all chat sessions belonging to a specific user, sorted by creation date descending."""
    result = await db.execute(
        select(Session)
        .where(Session.user_id == user_id)
        .order_by(Session.created_at.desc())
    )
    return list(result.scalars().all())

async def get_session_by_id(db: AsyncSession, session_id: uuid.UUID) -> Optional[Session]:
    """Perform a global lookup for a session by its UUID."""
    result = await db.execute(select(Session).where(Session.id == session_id))
    return result.scalar_one_or_none()

async def get_session(db: AsyncSession, session_id: uuid.UUID, user_id: uuid.UUID) -> Optional[Session]:
    """Retrieve a session by its ID and user ID."""
    result = await db.execute(
        select(Session).where(Session.id == session_id, Session.user_id == user_id)
    )
    return result.scalar_one_or_none()

async def delete_session(db: AsyncSession, session: Session) -> None:
    """Delete a chat session from the database."""
    await db.delete(session)
    await db.commit()
