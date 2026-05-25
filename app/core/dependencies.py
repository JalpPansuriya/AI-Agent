import uuid
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.repositories import user_repo
from app.models.models import User

from fastapi.security import HTTPBearer

oauth2_scheme = HTTPBearer()

async def get_current_user(
    request: Request,
    token_auth = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = token_auth.credentials
    """Dependency to retrieve the currently authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Wrap decoding in a try-except to catch JWTError, ValueError, or any decoding issues
        payload = decode_access_token(token)
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = uuid.UUID(user_id_str)
    except Exception:
        # Prevent raw exceptions from propagating, returning a clean 401 Unauthorized
        raise credentials_exception

    user = await user_repo.get_by_id(db, user_id)
    if user is None:
        raise credentials_exception
        
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
        
    request.state.user = user
    return user

async def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency to verify that the authenticated user is an admin."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
    return current_user


class RateLimiter:
    def __init__(self, limit: int, window_seconds: int = 60, group: str = "default", use_user: bool = True):
        self.limit = limit
        self.window_seconds = window_seconds
        self.group = group
        self.use_user = use_user

    async def __call__(self, request: Request):
        # 1. Determine key identifier
        user_id = None
        if self.use_user:
            # Try from request state first
            user = getattr(request.state, "user", None)
            if user:
                user_id = user.id
            else:
                # Try to extract sub from Bearer token directly
                auth_header = request.headers.get("authorization")
                if auth_header and auth_header.startswith("Bearer "):
                    token = auth_header.split(" ")[1]
                    try:
                        payload = decode_access_token(token)
                        sub = payload.get("sub")
                        if sub:
                            user_id = uuid.UUID(sub)
                    except Exception:
                        pass
                        
        if user_id:
            identifier = str(user_id)
        else:
            # Fallback to client IP
            identifier = request.client.host if request.client else "unknown_ip"
            
        key = f"rate_limit:{self.group}:{identifier}"
        
        # 2. Check rate limit in Redis
        from app.core.redis import redis_client
        from app.services.rate_limiter import check_rate_limit
        import time
        
        is_allowed, remaining, reset_timestamp = await check_rate_limit(
            redis_client, key, self.limit, self.window_seconds
        )
        
        retry_after = max(0, reset_timestamp - int(time.time()))
        
        rate_limit_headers = {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(reset_timestamp),
        }
        
        # Always store rate limit headers on request.state to be injected in middleware later
        request.state.rate_limit_headers = rate_limit_headers
        
        if not is_allowed:
            rate_limit_headers["Retry-After"] = str(retry_after)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers=rate_limit_headers
            )
