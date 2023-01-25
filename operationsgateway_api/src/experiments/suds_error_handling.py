from functools import wraps
from http.client import IncompleteRead
import logging

from suds import MethodNotFound, ServiceNotFound, TypeNotFound, WebFault

from operationsgateway_api.src.exceptions import ExperimentDetailsError

log = logging.getLogger()


def suds_error_handling(wsdl_call):
    """
    Parameterised decorator to handle errors raised during the use of Suds, currently
    used to contact the Scheduler system to retrieve experiment details
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except WebFault as exc:
                raise ExperimentDetailsError(
                    f"Problem processing current Scheduler call ({wsdl_call}):"
                    f" {str(exc)}",
                ) from exc
            except TypeNotFound as exc:
                raise ExperimentDetailsError(
                    f"WSDL call to {wsdl_call} not constructed properly, could not be"
                    " processed",
                ) from exc
            except MethodNotFound as exc:
                raise ExperimentDetailsError(
                    f"Could not find WSDL call to {wsdl_call} using client",
                ) from exc
            except ServiceNotFound as exc:
                raise ExperimentDetailsError(
                    f"Could not find WSDL service: {wsdl_call}",
                ) from exc
            except IncompleteRead as exc:
                raise ExperimentDetailsError(
                    "Incomplete read, problem with HTTP request when calling"
                    f" {wsdl_call}",
                ) from exc

        return wrapper

    return decorator
