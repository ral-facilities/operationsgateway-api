import logging

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from operationsgateway_api.src.auth.jwt_handler import JwtHandler
from operationsgateway_api.src.constants import ROUTE_MAPPINGS
from operationsgateway_api.src.error_handling import endpoint_error_handling
from operationsgateway_api.src.exceptions import ForbiddenError


log = logging.getLogger()
security = HTTPBearer()


@endpoint_error_handling
async def authorise_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),  # noqa: B008
) -> str:
    """
    Method to check that a valid access token is passed as a Bearer token in the
    Authorization header.
    :param credentials: the access token
    :return: the access token (if verified)
    """
    access_token = credentials.credentials
    JwtHandler.verify_token(access_token)
    return access_token


@endpoint_error_handling
async def authorise_route(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),  # noqa: B008
) -> str:
    """
    Method to check that a valid access token is passed as a Bearer token in the
    Authorization header and that the user has specifically been granted access to this
    route in their database record.
    :param request: the (HTTP) Request object for the call to the endpoint
    :param credentials: the access token
    :return: the access token (if verified)
    """
    access_token = credentials.credentials
    payload_dict = JwtHandler.verify_token(access_token)
    request_endpoint_function = request.scope["endpoint"]
    endpoint_path_from_mapping = ROUTE_MAPPINGS[request_endpoint_function]
    log.debug("endpoint_path_from_mapping: %s", endpoint_path_from_mapping)
    if "authorised_routes" in payload_dict:
        if endpoint_path_from_mapping in payload_dict["authorised_routes"]:
            return access_token
    # getting this far means the user is not authorised for this endpoint
    msg = (
        f"User '{payload_dict['username']}' is not authorised "
        f"to use endpoint '{endpoint_path_from_mapping}'"
    )
    log.warning(msg)
    raise ForbiddenError(msg)
