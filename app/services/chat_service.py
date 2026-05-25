import hashlib
import json
import uuid
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.models import Session, Message
from app.repositories import session_repo, message_repo
from app.core.redis import redis_client
from app.services.ai_service import check_prompt_injection, call_openai

async def create_session(
    db: AsyncSession, user_id: uuid.UUID, title: Optional[str] = None
) -> Session:
    """Orchestrate creating a new chat session."""
    return await session_repo.create_session(db, user_id, title)

async def list_sessions(db: AsyncSession, user_id: uuid.UUID) -> List[Session]:
    """Orchestrate listing a user's chat sessions."""
    return await session_repo.get_sessions_by_user(db, user_id)

async def get_session_with_history(
    db: AsyncSession, session_id: uuid.UUID, user_id: uuid.UUID
) -> dict:
    """
    Retrieve a session along with its chronological message history.
    Verifies that the session exists and belongs to the authenticated user.
    """
    # 1. Fetch session globally by its ID
    session = await session_repo.get_session_by_id(db, session_id)
    
    # 2. If it does not exist, return a clean 404
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
        
    # 3. If it exists but is owned by a different user, return a clean 403
    if session.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden to this session",
        )

    # 4. Fetch chronological history of the session
    # INTEGRATION NOTE FOR PHASE 5: When loading history to pass to the AI in future phases,
    # we explicitly use settings.CHAT_HISTORY_LIMIT to constrain the query.
    messages = await message_repo.get_messages(
        db, session_id=session_id, limit=settings.CHAT_HISTORY_LIMIT
    )
    
    return {
        "id": session.id,
        "user_id": session.user_id,
        "title": session.title,
        "created_at": session.created_at,
        "updated_at": session.updated_at,
        "messages": messages,
    }

async def delete_session(db: AsyncSession, session_id: uuid.UUID, user_id: uuid.UUID) -> None:
    """
    Delete a user's chat session.
    Verifies that the session exists and belongs to the authenticated user.
    """
    session = await session_repo.get_session_by_id(db, session_id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
        
    if session.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden to this session",
        )
        
    await session_repo.delete_session(db, session)

async def send_message(
    db: AsyncSession, session_id: uuid.UUID, user_id: uuid.UUID, content: str
) -> Message:
    """
    Save the user message, check prompt guard and Redis cache, call OpenAI, and save/return assistant reply.
    Verifies that the session exists and belongs to the authenticated user.
    """
    # 1. Verify session exists and belongs to the authenticated user
    session = await session_repo.get_session_by_id(db, session_id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
        
    if session.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden to this session",
        )

    # 2. Check for prompt injection BEFORE saving or processing
    if check_prompt_injection(content):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Potential prompt injection detected",
        )

    # 3. Load historical messages (up to CHAT_HISTORY_LIMIT) to build context
    history_msgs = await message_repo.get_messages(
        db, session_id=session_id, limit=settings.CHAT_HISTORY_LIMIT
    )

    SYSTEM_PROMPT = "You are an AI customer support assistant and recommendation engine. Be helpful, professional, and concise."

    # 4. Construct payload for OpenAI
    messages_payload = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in history_msgs:
        messages_payload.append({"role": m.role, "content": m.content})
    messages_payload.append({"role": "user", "content": content})

    # 5. Generate deterministic cache key using json.dumps with sort_keys=True
    serialized_payload = json.dumps(messages_payload, sort_keys=True)
    cache_key = f"chat_cache:{hashlib.sha256(serialized_payload.encode('utf-8')).hexdigest()}"

    # 6. Check Redis cache
    cached_val = await redis_client.get(cache_key)
    if cached_val:
        cached_data = json.loads(cached_val)
        assistant_content = cached_data["content"]
        prompt_tokens = cached_data.get("prompt_tokens", 0)
        completion_tokens = cached_data.get("completion_tokens", 0)
        total_tokens = cached_data.get("total_tokens", 0)
    else:
        # Call OpenAI on cache miss
        assistant_content, tokens = await call_openai(messages_payload)
        prompt_tokens = tokens["prompt_tokens"]
        completion_tokens = tokens["completion_tokens"]
        total_tokens = tokens["total_tokens"]
        
        # Save in Redis cache with 1-hour TTL (3600 seconds)
        await redis_client.setex(
            cache_key,
            3600,
            json.dumps({
                "content": assistant_content,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens
            })
        )

    # 7. Save user's message in database
    await message_repo.save_message(
        db,
        session_id=session_id,
        role="user",
        content=content,
    )

    # 8. Save assistant's response in database (with actual token counts)
    assistant_message = await message_repo.save_message(
        db,
        session_id=session_id,
        role="assistant",
        content=assistant_content,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens
    )

    # 9. Dynamically retrieve and attach product recommendations
    from app.services import recommendation_service
    recs = await recommendation_service.get_recommendations(db, session_id=session_id, user_id=user_id)
    assistant_message.recommendations = recs

    return assistant_message
