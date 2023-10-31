from http import HTTPStatus
import logging

from fastapi import APIRouter, Body, Depends, Path, Response, status
from fastapi.responses import JSONResponse

from operationsgateway_api.src.auth.authorisation import authorise_token
from operationsgateway_api.src.auth.jwt_handler import JwtHandler
from operationsgateway_api.src.error_handling import endpoint_error_handling
from operationsgateway_api.src.exceptions import MissingAttributeError
from operationsgateway_api.src.users.preferences import UserPreferences


log = logging.getLogger()
router = APIRouter()


@router.get(
    "/users/preferences/{name}",
    summary="Retrieve a user preference value",
    response_description="Value of the user preference for the logged in user",
    responses={
        404: {
            "description": "User does not have a value set for this preference",
        },
    },
    tags=["User Preferences"],
)
@endpoint_error_handling
async def get_user_preference(
    name: str = Path(
        ...,
        description="`name` of the user preference to fetch from the database",
    ),
    access_token: str = Depends(authorise_token),
):
    """
    Get a user preference by its name
    """

    token_payload = JwtHandler.get_payload(access_token)
    username = token_payload["username"]

    log.info("Getting user preference %s for user %s", name, username)
    try:
        content = await UserPreferences.get(username, name)
    except MissingAttributeError:
        log.error("User preference %s not found for user %s", name, username)
        raise
    return JSONResponse(content)


@router.delete(
    "/users/preferences/{name}",
    summary="Delete a specific user preference",
    response_description="No content",
    status_code=204,
    responses={
        404: {
            "description": "User does not have a value set for this preference",
        },
    },
    tags=["User Preferences"],
)
@endpoint_error_handling
async def delete_user_preference(
    name: str = Path(
        ...,
        description="`name` of the user preference to delete from the user's record",
    ),
    access_token: str = Depends(authorise_token),
):
    """
    Delete a user preference from a user's record
    """

    token_payload = JwtHandler.get_payload(access_token)
    username = token_payload["username"]

    log.info("Request to delete user preference %s for user %s", name, username)
    # first check that the preference is already set
    # if not an error will be raised
    try:
        await UserPreferences.get(username, name)
    except MissingAttributeError:
        log.error(
            "Failed to delete user preference %s for user %s. Preference is not set.",
            name,
            username,
        )
        raise
    # then go ahead and delete it
    await UserPreferences.delete(username, name)
    return Response(status_code=HTTPStatus.NO_CONTENT.value)


@router.post(
    "/users/preferences",
    summary="Store a user preference into the user's record in the database",
    response_description="No content",
    status_code=201,
    tags=["User Preferences"],
)
@endpoint_error_handling
async def save_user_preference(
    name: str = Body(
        ...,
        description="Name of the user preference",
    ),
    # specifically don't give a type hint to value
    # otherwise it can be coerced into the wrong type
    value=Body(
        ...,
        description="Value to save for the user preference",
    ),
    access_token: str = Depends(authorise_token),
):
    """
    Save/update a user preference into the database.
    If a value already exists for that preference then overwrite it.
    """

    token_payload = JwtHandler.get_payload(access_token)
    username = token_payload["username"]

    log.info("Saving user preference %s for user %s", name, username)

    await UserPreferences.insert(username, name, value)

    return Response(
        status_code=status.HTTP_201_CREATED,
        headers={"Location": f"/users/preferences/{name}"},
    )
