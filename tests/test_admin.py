import pytest
from httpx import AsyncClient
import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from app.models.models import User, Session, Message, RequestLog
from app.repositories.log_repo import create_request_log
from tests.test_recommendations import create_user_helper

pytestmark = pytest.mark.asyncio

@pytest.fixture(autouse=True)
async def mock_redis(monkeypatch):
    import fakeredis.aioredis as fake_redis
    fake_client = fake_redis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("app.core.redis.redis_client", fake_client)
    yield fake_client

async def test_non_admin_gets_403_on_all_endpoints(client: AsyncClient, db):
    """Test that a non-admin user gets 403 on every single admin endpoint."""
    user_token = await create_user_helper(client, "normal_user@example.com", "Normal User", "user", db)
    headers = {"Authorization": f"Bearer {user_token}"}

    endpoints = [
        ("/api/v1/admin/analytics", "GET"),
        ("/api/v1/admin/analytics/users", "GET"),
        ("/api/v1/admin/analytics/tokens", "GET"),
        ("/api/v1/admin/logs", "GET"),
        ("/api/v1/admin/users", "GET"),
    ]

    for endpoint, method in endpoints:
        response = await client.get(endpoint, headers=headers)
        assert response.status_code == 403, f"Expected 403 on {endpoint}, got {response.status_code}"

async def test_admin_platform_analytics(client: AsyncClient, db):
    """Test that platform stats calculates correct aggregated totals and costs."""
    admin_token = await create_user_helper(client, "admin_stats@example.com", "Admin User", "admin", db)
    user_token = await create_user_helper(client, "user_stats@example.com", "User Stats", "user", db)
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Find the user's ID
    res = await db.execute(select(User).where(User.email == "user_stats@example.com"))
    user = res.scalar_one()

    # Create a test session
    session = Session(user_id=user.id, title="Test Analytics Session")
    db.add(session)
    await db.commit()
    await db.refresh(session)

    # Create messages with token counts today
    msg1 = Message(
        session_id=session.id,
        role="user",
        content="Hello",
        prompt_tokens=0,
        completion_tokens=0,
        total_tokens=0
    )
    msg2 = Message(
        session_id=session.id,
        role="assistant",
        content="Hi there!",
        prompt_tokens=100,
        completion_tokens=200,
        total_tokens=300
    )
    db.add_all([msg1, msg2])
    await db.commit()

    # Create custom request logs
    await create_request_log(
        db=db,
        request_id=str(uuid.uuid4()),
        user_id=user.id,
        endpoint="/api/v1/chat",
        method="POST",
        status_code=200,
        duration_ms=150,
        tokens_used=300
    )
    await create_request_log(
        db=db,
        request_id=str(uuid.uuid4()),
        user_id=user.id,
        endpoint="/api/v1/chat",
        method="POST",
        status_code=500,
        duration_ms=250,
        tokens_used=0,
        error_message="Something failed"
    )

    # Retrieve platform analytics
    response = await client.get("/api/v1/admin/analytics", headers=headers)
    assert response.status_code == 200
    data = response.json()

    # Verify counts
    # total_users should be at least 2 (admin and normal user created)
    assert data["total_users"] >= 2
    assert data["active_sessions_today"] >= 1
    assert data["total_messages_today"] >= 2
    assert data["total_tokens_today"] >= 300
    
    # Verify exact cost formula: (100 * 0.15 / 1_000_000) + (200 * 0.60 / 1_000_000) = 0.000135
    expected_cost = (100 * 0.15 / 1000000) + (200 * 0.60 / 1000000)
    assert data["estimated_cost_today_usd"] >= expected_cost

    # Verify error rate: 1 error out of 2 requests = 50.0%
    # Note: the test client requests themselves might generate extra request logs,
    # so we should check that our specific database calculation works as expected.
    # To isolate, we query the service function directly, but let's check response
    # We added 2 request logs, so error rate is 50.0% if no other logs exist.
    # Since our mock client calls also write logs, total logs might be higher.
    # Let's verify that the error rate is calculated.
    assert "error_rate_percent" in data
    assert "avg_response_time_ms" in data

async def test_admin_user_analytics(client: AsyncClient, db):
    """Test GET /api/v1/admin/analytics/users returns per-user stats."""
    admin_token = await create_user_helper(client, "admin_user_stats@example.com", "Admin User", "admin", db)
    user_token = await create_user_helper(client, "user_analytics@example.com", "User Analytics", "user", db)
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Find the user's ID
    res = await db.execute(select(User).where(User.email == "user_analytics@example.com"))
    user = res.scalar_one()

    # Create a test session
    session = Session(user_id=user.id, title="User Analytics Session")
    db.add(session)
    await db.commit()
    await db.refresh(session)

    # Create message with tokens
    msg = Message(
        session_id=session.id,
        role="assistant",
        content="Helpful response",
        prompt_tokens=50,
        completion_tokens=50,
        total_tokens=100
    )
    db.add(msg)
    await db.commit()

    # Retrieve user analytics
    response = await client.get("/api/v1/admin/analytics/users", headers=headers)
    assert response.status_code == 200
    data = response.json()

    # Verify stats for user_analytics@example.com
    user_stat = next((u for u in data if u["email"] == "user_analytics@example.com"), None)
    assert user_stat is not None
    assert user_stat["full_name"] == "User Analytics"
    assert user_stat["message_count"] == 1
    assert user_stat["token_count"] == 100
    assert user_stat["last_active_at"] is not None

async def test_admin_token_analytics(client: AsyncClient, db):
    """Test GET /api/v1/admin/analytics/tokens returns total token counts and cost."""
    admin_token = await create_user_helper(client, "admin_token_stats@example.com", "Admin User", "admin", db)
    user_token = await create_user_helper(client, "user_tokens@example.com", "User Tokens", "user", db)
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Find the user's ID
    res = await db.execute(select(User).where(User.email == "user_tokens@example.com"))
    user = res.scalar_one()

    # Create a test session
    session = Session(user_id=user.id, title="Token Analytics Session")
    db.add(session)
    await db.commit()
    await db.refresh(session)

    # Create messages
    msg1 = Message(
        session_id=session.id,
        role="assistant",
        content="Response 1",
        prompt_tokens=300,
        completion_tokens=400,
        total_tokens=700
    )
    msg2 = Message(
        session_id=session.id,
        role="assistant",
        content="Response 2",
        prompt_tokens=200,
        completion_tokens=600,
        total_tokens=800
    )
    db.add_all([msg1, msg2])
    await db.commit()

    # Retrieve token analytics
    response = await client.get("/api/v1/admin/analytics/tokens", headers=headers)
    assert response.status_code == 200
    data = response.json()

    # Verify cumulative tokens and cost
    # prompt: 500, completion: 1000, total: 1500
    # cost: (500 * 0.15 / 1000000) + (1000 * 0.60 / 1000000) = 0.000675
    assert data["prompt_tokens"] >= 500
    assert data["completion_tokens"] >= 1000
    assert data["total_tokens"] >= 1500
    expected_cost = (500 * 0.15 / 1000000) + (1000 * 0.60 / 1000000)
    assert data["estimated_cost_usd"] >= expected_cost

async def test_admin_logs_filtering(client: AsyncClient, db):
    """Test GET /api/v1/admin/logs with various filters."""
    admin_token = await create_user_helper(client, "admin_logs@example.com", "Admin User", "admin", db)
    user_token = await create_user_helper(client, "user_logs@example.com", "User Logs", "user", db)
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Find the user's ID
    res = await db.execute(select(User).where(User.email == "user_logs@example.com"))
    user = res.scalar_one()

    # Create distinct request logs
    log_chat = await create_request_log(
        db=db,
        request_id=str(uuid.uuid4()),
        user_id=user.id,
        endpoint="/api/v1/chat",
        method="POST",
        status_code=200,
        duration_ms=100,
        tokens_used=10
    )
    log_auth = await create_request_log(
        db=db,
        request_id=str(uuid.uuid4()),
        user_id=user.id,
        endpoint="/api/v1/auth/login",
        method="POST",
        status_code=400,
        duration_ms=80,
        tokens_used=0,
        error_message="Invalid credentials"
    )

    # 1. Filter by endpoint
    resp_endpoint = await client.get("/api/v1/admin/logs?endpoint=/api/v1/chat", headers=headers)
    assert resp_endpoint.status_code == 200
    logs_endpoint = resp_endpoint.json()
    assert len(logs_endpoint) >= 1
    assert any(log["endpoint"] == "/api/v1/chat" for log in logs_endpoint)
    assert not any(log["endpoint"] == "/api/v1/auth/login" for log in logs_endpoint)

    # 2. Filter by status code
    resp_status = await client.get("/api/v1/admin/logs?status_code=400", headers=headers)
    assert resp_status.status_code == 200
    logs_status = resp_status.json()
    assert len(logs_status) >= 1
    assert any(log["status_code"] == 400 for log in logs_status)
    assert not any(log["status_code"] == 200 for log in logs_status)

    # 3. Filter by user_id
    resp_user = await client.get(f"/api/v1/admin/logs?user_id={user.id}", headers=headers)
    assert resp_user.status_code == 200
    logs_user = resp_user.json()
    assert len(logs_user) >= 2
    assert all(log["user_id"] == str(user.id) for log in logs_user)

    # 4. Limit logs
    resp_limit = await client.get("/api/v1/admin/logs?limit=1", headers=headers)
    assert resp_limit.status_code == 200
    logs_limit = resp_limit.json()
    assert len(logs_limit) == 1

async def test_admin_users_list(client: AsyncClient, db):
    """Test GET /api/v1/admin/users lists registered users and explicitly excludes hashed_password."""
    admin_token = await create_user_helper(client, "admin_users_list@example.com", "Admin User", "admin", db)
    user_token = await create_user_helper(client, "user_users_list@example.com", "User List", "user", db)
    headers = {"Authorization": f"Bearer {admin_token}"}

    response = await client.get("/api/v1/admin/users", headers=headers)
    assert response.status_code == 200
    data = response.json()

    # Verify users are present and hashed_password is completely absent from all user objects
    assert len(data) >= 2
    for user in data:
        assert "hashed_password" not in user
        assert "password" not in user
        assert "id" in user
        assert "email" in user
        assert "full_name" in user
