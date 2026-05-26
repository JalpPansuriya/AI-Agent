from datetime import datetime
import uuid
from typing import List
from fastapi import APIRouter, Depends, status, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, RateLimiter
from app.models.models import User
from app.schemas.chat import (
    SessionCreate,
    SessionResponse,
    MessageCreate,
    MessageResponse,
    SessionWithHistoryResponse,
)
from app.services import chat_service
from app.repositories import session_repo

router = APIRouter(tags=["chat"])

@router.post(
    "/chat/sessions",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new chat session",
    description="Creates a new chat session for the authenticated user."
)
async def create_session(
    request: SessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await chat_service.create_session(db, user_id=current_user.id, title=request.title)

@router.get(
    "/chat/sessions",
    response_model=List[SessionResponse],
    status_code=status.HTTP_200_OK,
    summary="List all chat sessions",
    description="Retrieves a list of all chat sessions belonging to the authenticated user."
)
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await chat_service.list_sessions(db, user_id=current_user.id)

@router.get(
    "/chat/sessions/{session_id}",
    response_model=SessionWithHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve session history",
    description="Retrieves a single chat session with its chronological message history. Scoped to the owner."
)
async def get_session_history(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await chat_service.get_session_with_history(
        db, session_id=session_id, user_id=current_user.id
    )

@router.get(
    "/chat/sessions/{session_id}/messages",
    response_model=List[MessageResponse],
    status_code=status.HTTP_200_OK,
    summary="List messages in a session",
    description="Returns all messages in chronological order for a session scoped to the authenticated user."
)
async def get_session_messages(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.repositories import message_repo
    session = await session_repo.get_session_by_id(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access forbidden")
    messages = await message_repo.get_messages(db, session_id=session_id)
    return messages

@router.delete(
    "/chat/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a chat session",
    description="Deletes a chat session belonging to the authenticated user."
)
async def delete_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await chat_service.delete_session(db, session_id=session_id, user_id=current_user.id)
    return None

@router.post(
    "/chat/sessions/{session_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Send a message",
    description="Sends a chat message to a session. Generates and returns a placeholder assistant reply."
)
async def send_message(
    session_id: uuid.UUID,
    request: MessageCreate,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _rate_limit: None = Depends(RateLimiter(limit=30, group="chat")),
):
    assistant_message = await chat_service.send_message(
        db, session_id=session_id, user_id=current_user.id, content=request.content
    )
    http_request.state.tokens_used = assistant_message.total_tokens
    return assistant_message

@router.put(
    "/chat/sessions/{session_id}",
    response_model=SessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a chat session",
    description="Updates the title of a chat session. Only the session owner may rename it."
)
async def update_session(
    session_id: uuid.UUID,
    data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    session = await session_repo.get_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    title = data.get("title", session.title)
    session.title = title
    session.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(session)
    return session
