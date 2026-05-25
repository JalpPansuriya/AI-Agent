import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class SessionCreate(BaseModel):
    title: Optional[str] = Field(None, max_length=255, description="Optional title of the chat session")

class SessionResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }

class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, description="Message content must be non-empty")

from app.schemas.product import ProductResponse

class MessageResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    role: str
    content: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    created_at: datetime
    recommendations: Optional[List[ProductResponse]] = None

    model_config = {
        "from_attributes": True
    }

class SessionWithHistoryResponse(SessionResponse):
    messages: List[MessageResponse]
