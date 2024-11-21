from functools import wraps

from requests import HTTPError, RequestException, Timeout
from requests.exceptions import ConnectionError

from operationsgateway_api.src.exceptions import ExperimentDetailsError


def rest_error_handling(endpoint_name):
    """
    Parameterised decorator to handle errors raised during the use of the REST API for
    the User Office (used to login where the session ID is used to access the Scheduler)
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except ConnectionError as exc:
                raise ExperimentDetailsError("Connection error occurred") from exc
            except HTTPError as exc:
                raise ExperimentDetailsError(
                    "A HTTP error occurred when trying to retrieve experiment data from"
                    f" {endpoint_name} on the external system",
                ) from exc
            except Timeout as exc:
                raise ExperimentDetailsError(
                    f"Request to {endpoint_name} to retrieve experiment data from the"
                    " external system has timed out",
                ) from exc
            except RequestException as exc:
                raise ExperimentDetailsError(
                    f"Something went wrong when accessing {endpoint_name} to retrieve"
                    " experiment data from an external system",
                ) from exc

        return wrapper

    return decorator
