import time
from typing import Tuple

async def check_rate_limit(
    redis_client,
    key: str,
    limit: int,
    window_seconds: int = 60
) -> Tuple[bool, int, int]:
    """
    Check if a key exceeds the rate limit.
    Uses a Redis atomic transaction to increment the count and fetch the TTL.
    If the key is new, its TTL will be set.
    Returns:
        (is_allowed: bool, remaining: int, reset_timestamp: int)
    """
    async with redis_client.pipeline(transaction=True) as pipe:
        pipe.incr(key)
        pipe.ttl(key)
        results = await pipe.execute()
        
    current_count = results[0]
    ttl = results[1]
    
    # If the key was just created, it will have a TTL of -1 or less.
    # Set the expiration.
    if ttl < 0:
        async with redis_client.pipeline(transaction=True) as pipe:
            pipe.expire(key, window_seconds)
            pipe.ttl(key)
            ttl_results = await pipe.execute()
        ttl = ttl_results[1]
        # Fallback if TTL is still negative
        if ttl < 0:
            ttl = window_seconds
            
    is_allowed = current_count <= limit
    remaining = max(0, limit - current_count)
    reset_timestamp = int(time.time()) + ttl
    
    return is_allowed, remaining, reset_timestamp
