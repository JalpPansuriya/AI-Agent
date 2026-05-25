import pytest
from httpx import AsyncClient
import uuid
from unittest.mock import patch
from sqlalchemy import select
from app.models.models import RequestLog, User

pytestmark = pytest.mark.asyncio

@pytest.fixture(autouse=True)
async def mock_redis(monkeypatch):
    import fakeredis.aioredis as fake_redis
    fake_client = fake_redis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("app.core.redis.redis_client", fake_client)
    yield fake_client

async def test_auth_rate_limiting(client: AsyncClient, db):
    # Auth rate limit is 10 per minute, use_user=False (limits by IP)
    # We send 10 signup requests, the 11th should return 429
    
    # Clean database request logs to start fresh
    await db.execute(RequestLog.__table__.delete())
    await db.commit()

    # Send 10 login requests
    for i in range(10):
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": f"nonexistent{i}@example.com",
                "password": "Password123"
            }
        )
        # Login will fail with 401 Unauthorized because credentials don't exist,
        # but the request itself went through and was rate limited
        assert response.status_code == 401
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers
        
    # The 11th request must return 429 Too Many Requests
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "Password123"
        }
    )
    assert response.status_code == 429
    assert response.json()["detail"] == "Rate limit exceeded"
    assert response.headers["X-RateLimit-Limit"] == "10"
    assert response.headers["X-RateLimit-Remaining"] == "0"
    assert "Retry-After" in response.headers
    assert int(response.headers["Retry-After"]) >= 0
    assert int(response.headers["X-RateLimit-Reset"]) > 0

    # Verify request logs in DB
    result = await db.execute(select(RequestLog))
    logs = list(result.scalars().all())
    # Should have 11 logs (10 unauthorized + 1 rate limited)
    assert len(logs) == 11
    
    rate_limit_logs = [l for l in logs if l.status_code == 429]
    assert len(rate_limit_logs) == 1
    for log in logs:
        assert log.endpoint == "/api/v1/auth/login"
        assert log.method == "POST"
        assert log.duration_ms >= 0
        assert log.tokens_used == 0

@patch("app.services.chat_service.call_openai")
async def test_chat_rate_limiting(mock_call_openai, client: AsyncClient, db):
    # 1. Create a user and log in to get a token
    signup_resp = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "chat_limiter@example.com",
            "password": "Password123",
            "full_name": "Chat Limiter"
        }
    )
    assert signup_resp.status_code == 201
    
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "chat_limiter@example.com",
            "password": "Password123"
        }
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Create a session
    session_resp = await client.post(
        "/api/v1/chat/sessions",
        json={"title": "Limiter Session"},
        headers=headers
    )
    assert session_resp.status_code == 201
    session_id = session_resp.json()["id"]
    
    # Mock openai response
    mock_call_openai.return_value = (
        "This is an automated reply.",
        {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20}
    )
    
    # Clean logs first (this ignores the signup/login logs for this test isolation)
    await db.execute(RequestLog.__table__.delete())
    await db.commit()
    
    # Send 30 messages (chat limit is 30)
    for i in range(30):
        response = await client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={"content": f"Message {i}"},
            headers=headers
        )
        assert response.status_code == 200
        assert response.headers["X-RateLimit-Limit"] == "30"
        assert int(response.headers["X-RateLimit-Remaining"]) >= 0
        
    # The 31st request must return 429
    response = await client.post(
        f"/api/v1/chat/sessions/{session_id}/messages",
        json={"content": "Message 31"},
        headers=headers
    )
    assert response.status_code == 429
    assert response.headers["X-RateLimit-Remaining"] == "0"
    assert int(response.headers["X-RateLimit-Reset"]) > 0
    assert int(response.headers["Retry-After"]) >= 0
    
    # Verify request logs in DB
    result = await db.execute(select(RequestLog))
    logs = list(result.scalars().all())
    # Should have 31 logs (30 successful messages + 1 rate limited message)
    assert len(logs) == 31
    
    # Verify that the correct user_id is logged
    user_result = await db.execute(select(User).where(User.email == "chat_limiter@example.com"))
    user = user_result.scalar_one()
    
    success_logs = [l for l in logs if l.status_code == 200]
    assert len(success_logs) == 30
    for l in success_logs:
        assert l.user_id == user.id
        assert l.tokens_used == 20
        assert l.endpoint == f"/api/v1/chat/sessions/{session_id}/messages"
        
    rate_limit_logs = [l for l in logs if l.status_code == 429]
    assert len(rate_limit_logs) == 1
    assert rate_limit_logs[0].user_id == user.id
    assert rate_limit_logs[0].tokens_used == 0
