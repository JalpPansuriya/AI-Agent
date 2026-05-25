from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
)
from app.repositories import user_repo
from app.schemas.auth import SignupRequest, LoginRequest, TokenResponse, UserResponse

async def signup(db: AsyncSession, request: SignupRequest) -> UserResponse:
    """Handle user registration workflow."""
    # Check if user already exists
    existing_user = await user_repo.get_by_email(db, request.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Hash the plain password
    hashed = hash_password(request.password)

    # Create the user record
    user = await user_repo.create_user(
        db, email=request.email, hashed_password=hashed, full_name=request.full_name
    )
    return UserResponse.model_validate(user)

async def login(db: AsyncSession, request: LoginRequest) -> TokenResponse:
    """Handle user login and authentication workflow."""
    # Retrieve user by email
    user = await user_repo.get_by_email(db, request.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Verify user password
    if not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is disabled",
        )

    # Create tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    opaque_refresh_token = create_refresh_token()

    # Calculate refresh token expiration
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    # Save refresh token in DB
    await user_repo.create_refresh_token(
        db, user_id=user.id, token=opaque_refresh_token, expires_at=expires_at
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=opaque_refresh_token,
    )

async def refresh(db: AsyncSession, refresh_token: str) -> TokenResponse:
    """Handle refresh token rotation (RTR) workflow."""
    # Lookup the refresh token in database
    rt_record = await user_repo.get_refresh_token(db, refresh_token)
    if not rt_record or rt_record.is_revoked:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Ensure expiration time is offset-aware or compared properly
    now = datetime.now(timezone.utc)
    # db value expires_at might be timezone aware or naive.
    # In models.py we defined DateTime(timezone=True) so it is offset-aware
    if rt_record.expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Revoke the old token (Rotate)
    await user_repo.revoke_refresh_token(db, rt_record.id)

    # Issue a new access token and a new opaque refresh token
    new_access_token = create_access_token(data={"sub": str(rt_record.user_id)})
    new_opaque_refresh_token = create_refresh_token()
    new_expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    # Save the new refresh token in DB
    await user_repo.create_refresh_token(
        db, user_id=rt_record.user_id, token=new_opaque_refresh_token, expires_at=new_expires_at
    )

    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_opaque_refresh_token,
    )

async def logout(db: AsyncSession, refresh_token: str) -> None:
    """Handle user logout workflow by revoking the refresh token."""
    rt_record = await user_repo.get_refresh_token(db, refresh_token)
    if rt_record:
        await user_repo.revoke_refresh_token(db, rt_record.id)
