"""Simple TTL cache for API responses."""

import time
from functools import wraps
from typing import Any, Callable

# In-memory cache storage
_cache: dict[str, tuple[Any, float]] = {}

DEFAULT_TTL = 30  # 30 seconds


def timed_cache(ttl: int = DEFAULT_TTL):
    """
    Decorator that caches function results with a TTL.

    Args:
        ttl: Time-to-live in seconds
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            key = f"{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"

            # Check if cached and not expired
            if key in _cache:
                result, timestamp = _cache[key]
                if time.time() - timestamp < ttl:
                    return result

            # Call function and cache result
            result = await func(*args, **kwargs)
            _cache[key] = (result, time.time())
            return result

        return wrapper
    return decorator


def clear_cache():
    """Clear the entire cache."""
    _cache.clear()


def invalidate_pattern(pattern: str):
    """Invalidate cache entries matching a pattern."""
    keys_to_delete = [k for k in _cache.keys() if pattern in k]
    for key in keys_to_delete:
        del _cache[key]
