import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.core.config import settings
from app.repositories import session_repo, message_repo
from app.services.ai_service import check_prompt_injection, stream_openai

router = APIRouter(tags=["websocket"])

@router.websocket("/ws/chat/{session_id}")
async def websocket_chat(
    websocket: WebSocket,
    session_id: uuid.UUID,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    WebSocket endpoint for real-time bi-directional streaming chat.
    Authenticates token from query parameters and scopes the session to the owner.
    """
    # 1. Authenticate token
    try:
        payload = decode_access_token(token)
        user_id_str = payload.get("sub")
        if not user_id_str:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        user_id = uuid.UUID(user_id_str)
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # 2. Accept connection
    await websocket.accept()

    # 3. Check session existence and ownership
    session = await session_repo.get_session_by_id(db, session_id)
    if not session or session.user_id != user_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        while True:
            # Receive user message in JSON format: {"content": "your message"}
            data = await websocket.receive_json()
            user_content = data.get("content", "").strip()
            
            if not user_content:
                continue

            # 4. Check for prompt injection
            if check_prompt_injection(user_content):
                await websocket.send_json({"error": "Potential prompt injection detected"})
                continue

            # 5. Save user message in DB
            await message_repo.save_message(
                db,
                session_id=session_id,
                role="user",
                content=user_content,
            )

            # 6. Load history to build context
            history_msgs = await message_repo.get_messages(
                db, session_id=session_id, limit=settings.CHAT_HISTORY_LIMIT
            )

            SYSTEM_PROMPT = "You are an AI customer support assistant and recommendation engine. Be helpful, professional, and concise."

            messages_payload = [{"role": "system", "content": SYSTEM_PROMPT}]
            for m in history_msgs:
                messages_payload.append({"role": m.role, "content": m.content})

            # 7. Stream OpenAI response chunks
            full_response_chunks = []
            async for chunk in stream_openai(messages_payload):
                await websocket.send_json({"chunk": chunk})
                full_response_chunks.append(chunk)

            full_response_text = "".join(full_response_chunks)

            # 8. Save assistant's response in DB (approximate tokens to 0 for streaming)
            assistant_message = await message_repo.save_message(
                db,
                session_id=session_id,
                role="assistant",
                content=full_response_text,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
            )

            # 9. Send completion done signal
            await websocket.send_json({
                "done": True,
                "message_id": str(assistant_message.id),
                "total_tokens": 0,
            })

    except WebSocketDisconnect:
        pass
