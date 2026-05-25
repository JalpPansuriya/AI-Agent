from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, RateLimiter
from app.models.models import User
from app.schemas.auth import (
    SignupRequest,
    LoginRequest,
    TokenResponse,
    UserResponse,
    RefreshRequest,
)
from app.services import auth_service

router = APIRouter(tags=["authentication"])

@router.post(
    "/auth/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Creates a new user account. Returns user details without tokens."
)
async def signup(
    request: SignupRequest,
    db: AsyncSession = Depends(get_db),
    _rate_limit: None = Depends(RateLimiter(limit=10, group="auth", use_user=False))
):
    return await auth_service.signup(db, request)

@router.post(
    "/auth/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="User login",
    description="Authenticates user credentials and returns both access and refresh tokens."
)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
    _rate_limit: None = Depends(RateLimiter(limit=10, group="auth", use_user=False))
):
    return await auth_service.login(db, request)

@router.post(
    "/auth/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Rotate refresh token",
    description="Rotates the access and refresh tokens using a valid refresh token."
)
async def refresh(
    request: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    _rate_limit: None = Depends(RateLimiter(limit=10, group="auth", use_user=False))
):
    return await auth_service.refresh(db, request.refresh_token)

@router.post(
    "/auth/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="User logout",
    description="Revokes the provided refresh token so it cannot be used again."
)
async def logout(
    request: RefreshRequest,
    db: AsyncSession = Depends(get_db),
    _rate_limit: None = Depends(RateLimiter(limit=10, group="auth", use_user=False))
):
    await auth_service.logout(db, request.refresh_token)
    return None

@router.get(
    "/auth/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user info",
    description="Returns details about the currently authenticated user."
)
async def me(
    current_user: User = Depends(get_current_user),
    _rate_limit: None = Depends(RateLimiter(limit=10, group="auth", use_user=False))
):
    return UserResponse.model_validate(current_user)
