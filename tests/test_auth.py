import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

async def test_signup_success(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "test@example.com",
            "password": "Password123",
            "full_name": "Test User"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["full_name"] == "Test User"
    assert "id" in data
    assert data["role"] == "user"

async def test_signup_duplicate_email(client: AsyncClient):
    # Register first user
    await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "dup@example.com",
            "password": "Password123",
            "full_name": "First User"
        }
    )
    # Register second user with same email
    response = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "dup@example.com",
            "password": "DifferentPassword123",
            "full_name": "Second User"
        }
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Email already registered"

async def test_signup_weak_password(client: AsyncClient):
    # Too short
    response = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "weak1@example.com",
            "password": "Pass1",
            "full_name": "Weak User"
        }
    )
    assert response.status_code == 422

    # No uppercase
    response = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "weak2@example.com",
            "password": "password123",
            "full_name": "Weak User"
        }
    )
    assert response.status_code == 422

    # No number
    response = await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "weak3@example.com",
            "password": "Passwordabc",
            "full_name": "Weak User"
        }
    )
    assert response.status_code == 422

async def test_login_success(client: AsyncClient):
    # Register first
    await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "login@example.com",
            "password": "Password123",
            "full_name": "Login User"
        }
    )
    # Login
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "login@example.com",
            "password": "Password123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

async def test_login_wrong_password(client: AsyncClient):
    # Register first
    await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "wrongpass@example.com",
            "password": "Password123",
            "full_name": "Wrong Pass User"
        }
    )
    # Login with wrong password
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "wrongpass@example.com",
            "password": "WrongPassword123"
        }
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"

async def test_refresh_token_rotation(client: AsyncClient):
    # Register and login
    await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "refresh@example.com",
            "password": "Password123",
            "full_name": "Refresh User"
        }
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "refresh@example.com",
            "password": "Password123"
        }
    )
    tokens = login_resp.json()
    refresh_token = tokens["refresh_token"]

    # First refresh
    refresh_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    assert refresh_resp.status_code == 200
    new_tokens = refresh_resp.json()
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens
    assert new_tokens["refresh_token"] != refresh_token

    # Subsequent refresh with the old, rotated refresh token must fail (RTR check)
    fail_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    assert fail_resp.status_code == 401

async def test_protected_route(client: AsyncClient):
    # Hitting /auth/me without token -> 401
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401

    # Hitting with invalid token -> 401
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401

    # Register and login to get valid token
    await client.post(
        "/api/v1/auth/signup",
        json={
            "email": "protected@example.com",
            "password": "Password123",
            "full_name": "Protected User"
        }
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "protected@example.com",
            "password": "Password123"
        }
    )
    tokens = login_resp.json()
    access_token = tokens["access_token"]

    # Hitting with valid token -> 200
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "protected@example.com"
    assert data["full_name"] == "Protected User"
