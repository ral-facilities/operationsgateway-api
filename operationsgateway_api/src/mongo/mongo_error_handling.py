from functools import wraps
from inspect import iscoroutinefunction
import logging

from operationsgateway_api.src.exceptions import DatabaseError, DuplicateSessionError

log = logging.getLogger()


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
                except (DatabaseError, DuplicateSessionError):
                    raise  # If it's already a DatabaseError
                    # or DuplicateSessionError, propagate it as-is
                except Exception as exc:
                    log.error("Database operation: %s failed", operation)
                    raise DatabaseError(
                        f"Database operation failed during {operation}",
                    ) from exc

            return async_wrapper
        else:  # Handle synchronous functions

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except (DatabaseError, DuplicateSessionError):
                    raise  # If it's already a DatabaseError
                    # or DuplicateSessionError, propagate it as-is
                except Exception as exc:
                    log.error("Database operation: %s failed", operation)
                    raise DatabaseError(
                        f"Database operation failed during {operation}",
                    ) from exc

            return sync_wrapper

    return decorator
