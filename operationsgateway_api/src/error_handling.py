from fastapi import HTTPException
from functools import wraps
import logging

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
        except ApiError as e:
            log.error("Error in endpoint '%s': %s", method.__name__, e.args[0])
            raise HTTPException(e.status_code, e.args[0])
        except Exception as e:
            log.exception(msg=e.args, exc_info=1)
            # raise non-API errors as "unknown" server errors
            # for security reasons responses should not return messages that might 
            # reveal details about the configuration of the server
            raise HTTPException(status_code=500, detail="Unknown error")

    return wrapper_error_handling
