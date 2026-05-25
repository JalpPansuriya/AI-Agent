import uuid
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import Message

async def save_message(
    db: AsyncSession,
    session_id: uuid.UUID,
    role: str,
    content: str,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0,
) -> Message:
    """Save a chat message in the database."""
    message = Message(
        session_id=session_id,
        role=role,
        content=content,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message

async def get_messages(
    db: AsyncSession, session_id: uuid.UUID, limit: int = 100
) -> List[Message]:
    """Retrieve chat history messages for a session, ordered chronologically ascending."""
    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
        .limit(limit)
    )
    return list(result.scalars().all())
