from functools import wraps
import logging

from fastapi import HTTPException

from operationsgateway_api.src.exceptions import ApiError

log = logging.getLogger()


def endpoint_error_handling(method):
    """
    Decorator to handle errors raised up to the top level of the endpoint
    :param method: The method for the endpoint
    :raises: Any exception caught by the execution of `method`
    """

    @wraps(method)
    async def wrapper_error_handling(*args, **kwargs):
        try:
            return await method(*args, **kwargs)
        except ApiError as exc:
            log.error("Error in endpoint '%s': %s", method.__name__, exc.args[0])
            raise HTTPException(exc.status_code, exc.args[0]) from exc
        except Exception as exc:
            log.exception(msg=exc.args)
            # raise non-API errors as "unknown" server errors
            # for security reasons responses should not return messages that might
            # reveal details about the configuration of the server
            raise HTTPException(status_code=500, detail="Unknown error") from exc

    return wrapper_error_handling
