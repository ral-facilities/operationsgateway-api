import logging

from fastapi import APIRouter, Body, Cookie, Response, status, Depends
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing_extensions import Annotated

from operationsgateway_api.src.auth.authentication import Authentication
from operationsgateway_api.src.auth.jwt_handler import JwtHandler
from operationsgateway_api.src.auth.oidc_handler import OidcHandler
from operationsgateway_api.src.config import Config
from operationsgateway_api.src.error_handling import endpoint_error_handling
from operationsgateway_api.src.exceptions import ForbiddenError
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

    # # create their JWT access and refresh tokens
    jwt_handler = JwtHandler(user_model)
    access_token = jwt_handler.get_access_token()
    refresh_token = jwt_handler.get_refresh_token()
    log.info(
        "Refresh token assigned to '%s': %s",
        login_details.username,
        refresh_token,
    )
    response = JSONResponse(content=access_token)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=604800,
        secure=True,
        httponly=True,
        samesite="Lax",
        path="/refresh",
    )
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
    "/oidc_login",
    summary="Login using an OpenID Connect (OIDC) token",
    response_description="A JWT access token (and a refresh token cookie)",
    responses={
        401: {"description": "Invalid OIDC token"},
        403: {"description": "User not allowed to access the system"},
    },
    tags=["Authentication"],
)
@endpoint_error_handling
async def oidc_login(
    oidc_handler: Annotated[OidcHandler, Depends(OidcHandler)],
    bearer_token: Annotated[
        HTTPAuthorizationCredentials, Depends(HTTPBearer(description="OIDC ID token"))
    ],
):
    """
    This endpoint takes an OIDC token (usually from Keycloak), verifies it, and returns
    a JWT access token and refresh token for this API.
    """
    log.info("Received OIDC login request")

    encoded_token = bearer_token.credentials

    # Validate the OIDC token and extract claims (throws error if invalid)
    mechanism, oidc_email = oidc_handler.handle(encoded_token)
    log.debug("Validated OIDC claims: %s", oidc_email)

    # get fedID from email
    fedid = Authentication.get_fedid_from_email(oidc_email)

    # Construct a User model (or dummy object) to use with JwtHandler
    user_model = await User.get_user(
        fedid
    )
    if not user_model:
        log.warning("User '%s' not found in user database", fedid)
        raise ForbiddenError("User not authorised")

    # Create access/refresh tokens
    jwt_handler = JwtHandler(user_model)
    access_token = jwt_handler.get_access_token()
    refresh_token = jwt_handler.get_refresh_token()

    log.info("Refresh token issued for '%s'", fedid)
    response = JSONResponse(content=access_token)
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=604800,
        secure=True,
        httponly=True,
        samesite="Lax",
        path="/refresh",
    )
    return response

@router.get("/oidc_providers")
@endpoint_error_handling
async def list_oidc_providers():
    """
    Returns a list of available OIDC providers with display name,
    configuration URL, and client ID (audience).
    """
    providers = [
        {
            "display_name": name,
            "configuration_url": config.configuration_url,
            "client_id": config.audience,
        }
        for name, config in Config.config.auth.oidc_providers.items()
    ]
    return providers
