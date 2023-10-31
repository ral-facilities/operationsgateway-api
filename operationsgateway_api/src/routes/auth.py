import logging

from fastapi import APIRouter, Body, Cookie, Response, status
from fastapi.responses import JSONResponse
from typing_extensions import Annotated

from operationsgateway_api.src.auth.authentication import Authentication
from operationsgateway_api.src.auth.jwt_handler import JwtHandler
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
