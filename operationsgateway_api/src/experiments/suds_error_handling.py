from functools import wraps
import logging

from zeep.exceptions import (
    DTDForbidden,
    EntitiesForbidden,
    Error,
    Fault,
    TransportError,
    ValidationError,
    XMLParseError,
)

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
            except Fault as exc:
                raise ExperimentDetailsError(
                    f"Problem processing current Scheduler call ({wsdl_call}):"
                    f" {str(exc)}",
                ) from exc
            except TransportError as exc:
                raise ExperimentDetailsError(str(exc)) from exc
            except XMLParseError as exc:
                raise ExperimentDetailsError(
                    "Problem parsing XML during communication with Scheduler:"
                    f" {str(exc)}",
                ) from exc
            except ValidationError as exc:
                raise ExperimentDetailsError(
                    "Problem validating communication to the Scheduler",
                ) from exc
            except DTDForbidden as exc:
                raise ExperimentDetailsError(
                    "Document Type Declaration error while contacting Scheduler",
                ) from exc
            except EntitiesForbidden as exc:
                raise ExperimentDetailsError(
                    f"Entities forbidden in WSDL call: {str(exc)}",
                ) from exc
            except Error as exc:
                raise ExperimentDetailsError(
                    "Unexpected error from contacting the Scheduler",
                ) from exc

        return wrapper

    return decorator
