import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import User, RefreshToken

async def get_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """Retrieve a user by their email address."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()

async def get_by_id(db: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
    """Retrieve a user by their UUID."""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()

async def create_user(db: AsyncSession, email: str, hashed_password: str, full_name: str) -> User:
    """Create a new user in the database."""
    user = User(
        email=email,
        hashed_password=hashed_password,
        full_name=full_name,
        role="user",  # Default role
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def create_refresh_token(
    db: AsyncSession, user_id: uuid.UUID, token: str, expires_at: datetime
) -> RefreshToken:
    """Create a new refresh token entry in the database."""
    refresh_token = RefreshToken(
        user_id=user_id,
        token=token,
        expires_at=expires_at,
        is_revoked=False,
    )
    db.add(refresh_token)
    await db.commit()
    await db.refresh(refresh_token)
    return refresh_token

async def get_refresh_token(db: AsyncSession, token: str) -> Optional[RefreshToken]:
    """Retrieve a refresh token by its opaque string value."""
    result = await db.execute(select(RefreshToken).where(RefreshToken.token == token))
    return result.scalar_one_or_none()

async def revoke_refresh_token(db: AsyncSession, token_id: uuid.UUID) -> None:
    """Revoke a refresh token by marking it as revoked."""
    result = await db.execute(select(RefreshToken).where(RefreshToken.id == token_id))
    rt = result.scalar_one_or_none()
    if rt:
        rt.is_revoked = True
        await db.commit()
