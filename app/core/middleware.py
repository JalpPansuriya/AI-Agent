import time
import uuid
from datetime import datetime, timezone
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.database import AsyncSessionLocal
from app.repositories.log_repo import create_request_log
from loguru import logger

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Initialize default state values
        request.state.tokens_used = 0
        
        start_time = time.time()
        error_message = None
        response = None
        
        try:
            response = await call_next(request)
        except Exception as e:
            error_message = str(e)
            logger.exception(f"Unhandled exception in request {request_id}: {e}")
            raise e
        finally:
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Extract user_id from state if it was set
            user = getattr(request.state, "user", None)
            user_id = user.id if user else None
            
            # Extract tokens_used from state
            tokens_used = getattr(request.state, "tokens_used", 0)
            
            # Extract rate limit headers
            rate_limit_headers = getattr(request.state, "rate_limit_headers", {})
            
            # Determine status code
            status_code = response.status_code if response else 500
            
            # Log to DB asynchronously using a new db session or the overridden test session
            try:
                endpoint = request.url.path
                method = request.method
                
                from app.core.database import get_db
                from app.main import app
                
                if get_db in app.dependency_overrides:
                    # We are in test mode! Retrieve the active test transaction session.
                    override = app.dependency_overrides[get_db]
                    db_generator = override()
                    db = await db_generator.__anext__()
                    
                    await create_request_log(
                        db=db,
                        request_id=request_id,
                        user_id=user_id,
                        endpoint=endpoint,
                        method=method,
                        status_code=status_code,
                        duration_ms=duration_ms,
                        tokens_used=tokens_used,
                        error_message=error_message
                    )
                    
                    try:
                        await db_generator.__anext__()
                    except StopAsyncIteration:
                        pass
                else:
                    # In production, save log directly to DB (no Celery worker on Render)
                    try:
                        async with AsyncSessionLocal() as db:
                            await create_request_log(
                                db=db,
                                request_id=request_id,
                                user_id=user_id,
                                endpoint=endpoint,
                                method=method,
                                status_code=status_code,
                                duration_ms=duration_ms,
                                tokens_used=tokens_used,
                                error_message=error_message
                            )
                    except Exception as prod_log_err:
                        logger.error(f"Failed to save production request log: {prod_log_err}")
            except Exception as db_err:
                logger.error(f"Failed to save request log: {db_err}")
                
            # Log structured JSON request information via Loguru
            try:
                logger.bind(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    request_id=request_id,
                    user_id=str(user_id) if user_id else None,
                    method=request.method,
                    endpoint=request.url.path,
                    status_code=status_code,
                    duration_ms=duration_ms,
                    tokens_used=tokens_used,
                    error=error_message
                ).info(f"Processed request {request.method} {request.url.path} with status {status_code} in {duration_ms}ms")
            except Exception as log_err:
                logger.error(f"Failed to write structured JSON log: {log_err}")
                
            # If we have a response, inject X-Request-ID and X-RateLimit headers
            if response:
                response.headers["X-Request-ID"] = request_id
                for k, v in rate_limit_headers.items():
                    response.headers[k] = v
                    
        return response
