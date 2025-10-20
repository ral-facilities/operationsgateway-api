import logging

from fastapi import APIRouter, Body, Cookie, Depends, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing_extensions import Annotated

from operationsgateway_api.src.auth import oidc
from operationsgateway_api.src.auth.authentication import Authentication
from operationsgateway_api.src.auth.jwt_handler import JwtHandler
from operationsgateway_api.src.config import Config
from operationsgateway_api.src.error_handling import endpoint_error_handling
from operationsgateway_api.src.exceptions import ForbiddenError, UnauthorisedError
from operationsgateway_api.src.models import AccessTokenModel, LoginDetailsModel
from operationsgateway_api.src.users.user import User


log = logging.getLogger()
router = APIRouter()

token = Annotated[
    AccessTokenModel,
    Body(
        ...,
        description="JSON object containing the existing access token",
    ),
]


@router.post(
    "/login",
    summary="Login with a username and password",
    response_description="A JWT access token (and a refresh token cookie)",
    responses={
        401: {
            "description": "User not authorised (the user is not on the list of"
            " allowed users or login details were incorrect)",
        },
        500: {
            "description": "Login failed due to problems with the user's account"
            " record",
        },
    },
    tags=["Authentication"],
)
@endpoint_error_handling
async def login(
    login_details: Annotated[
        LoginDetailsModel,
        Body(
            ...,
            description="JSON object containing username and password",
        ),
    ],
):
    """
    This endpoint takes a username and password, authenticates the user and then
    returns a JWT access token in the response body and a JWT refresh token in a
    cookie.
    """
    log.info("Login request for '%s'", login_details.username)

    # authenticate the user
    user_model = await User.get_user(login_details.username)
    log.debug("user_model: %s", user_model)

    authentication = Authentication(login_details, user_model)
    authentication.authenticate()

    log.info(
        "Creating refresh token for '%s':",
        login_details.username,
    )

    response = Authentication.create_tokens_response(user_model)

    return response


@router.post(
    "/verify",
    summary="Verifies that a JWT token was created by this server",
    response_description="200 OK (no response body) if the token is verified",
    responses={
        403: {"description": "The token was invalid"},
    },
    tags=["Authentication"],
)
@endpoint_error_handling
async def verify(
    token: token,
):
    """
    This endpoint takes a JWT token that was issued by this service
    """
    log.debug("Verifying token: %s", token.token)
    JwtHandler.verify_token(token.token)
    return Response(status_code=status.HTTP_200_OK)


@router.post(
    "/refresh",
    summary="Generate an updated JWT access token using the JWT refresh token",
    response_description="A JWT access token",
    responses={
        403: {
            "description": "There was a problem with the refresh token or a problem"
            " updating the access token",
        },
    },
    tags=["Authentication"],
)
@endpoint_error_handling
async def refresh(
    token: token,
    refresh_token: str = Cookie(
        None,
        description="The JWT refresh token from a cookie",
    ),
):
    """
    This endpoint takes an existing JWT access token and extends the validity period of
    that token providing the supplied refresh token is still valid
    """
    log.debug("token.token (access token): %s", token.token)
    if refresh_token is None:
        raise ForbiddenError("No refresh token found")
    else:
        log.debug("refresh_token: %s", refresh_token)
    return JwtHandler.refresh_token(refresh_token, token.token)


@router.post(
    path="/oidc_login/{provider_id}",
    summary="Login using an OpenID Connect (OIDC) token",
    response_description="A JWT access token (and a refresh token cookie)",
    responses={401: {"description": "Unauthorized"}},
    tags=["Authentication"],
)
@endpoint_error_handling
async def oidc_login(
    provider_id: Annotated[str, "OIDC provider id"],
    bearer_token: Annotated[
        HTTPAuthorizationCredentials,
        Depends(HTTPBearer(description="OIDC ID token")),
    ],
):
    log.info("Received OIDC login request")
    id_token = bearer_token.credentials

    mechanism, oidc_username = oidc.get_username(provider_id, id_token)
    log.debug("Validated OIDC user via %s: %s", mechanism, oidc_username)

    user_model = await User.get_user_by_email(oidc_username)
    if not user_model:
        log.warning("User '%s' not found in user database", oidc_username)
        raise UnauthorisedError

    return Authentication.create_tokens_response(user_model)


@router.get(
    path="/oidc_providers",
    summary="Get a list of OIDC providers",
    response_description="Returns a list of OIDC providers",
    tags=["Authentication"],
)
@endpoint_error_handling
async def list_oidc_providers():
    log.info("Getting a list of OIDC providers")

    providers = {
        provider_id: {
            "display_name": cfg.display_name,
            "configuration_url": cfg.configuration_url,
            "client_id": cfg.client_id,
            "pkce": True,
            "scope": cfg.scope,
        }
        for provider_id, cfg in Config.config.auth.oidc_providers.items()
    }
    return providers
