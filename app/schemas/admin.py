import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr

class PlatformStatsResponse(BaseModel):
    total_users: int
    active_sessions_today: int
    total_messages_today: int
    total_tokens_today: int
    estimated_cost_today_usd: float
    error_rate_percent: float
    avg_response_time_ms: float

    model_config = {
        "from_attributes": True
    }


class UserStatsResponse(BaseModel):
    user_id: uuid.UUID
    email: EmailStr
    full_name: str
    message_count: int
    token_count: int
    last_active_at: Optional[datetime]

    model_config = {
        "from_attributes": True
    }


class TokenStatsResponse(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float

    model_config = {
        "from_attributes": True
    }


class LogResponse(BaseModel):
    id: uuid.UUID
    request_id: str
    user_id: Optional[uuid.UUID]
    endpoint: str
    method: str
    status_code: int
    duration_ms: int
    tokens_used: int
    error_message: Optional[str]
    created_at: datetime

    model_config = {
        "from_attributes": True
    }
