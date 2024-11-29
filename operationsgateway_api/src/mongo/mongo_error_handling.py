from functools import wraps
from inspect import iscoroutinefunction

from operationsgateway_api.src.exceptions import DatabaseError


def mongodb_error_handling(operation: str):
    """
    Decorator for consistent error handling in MongoDB operations, supporting both
    sync and async functions.
    """

    def decorator(func):
        if iscoroutinefunction(func):  # Check if the function is async

            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except Exception as exc:
                    raise DatabaseError(
                        f"Database operation failed during {operation}",
                    ) from exc

            return async_wrapper
        else:  # Handle synchronous functions

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    raise DatabaseError(
                        f"Database operation failed during {operation}",
                    ) from exc

            return sync_wrapper

    return decorator
