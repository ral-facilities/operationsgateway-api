from http import HTTPStatus
import logging

from fastapi import APIRouter, Body, Depends, Path, Response, status
from fastapi.responses import JSONResponse
from typing_extensions import Annotated

from operationsgateway_api.src.auth.authorisation import authorise_route
from operationsgateway_api.src.error_handling import endpoint_error_handling
from operationsgateway_api.src.exceptions import QueryParameterError, UnauthorisedError
from operationsgateway_api.src.models import UpdateUserModel, UserModel
from operationsgateway_api.src.mongo.interface import MongoDBInterface
from operationsgateway_api.src.users.user import User

log = logging.getLogger()
router = APIRouter()
AuthoriseRoute = Annotated[str, Depends(authorise_route)]


@router.post(
    "/users",
    summary="Create a user",
    response_description="The created user",
    tags=["Users"],
)
@endpoint_error_handling
async def add_user(
    access_token: AuthoriseRoute,
    login_details: Annotated[
        UserModel,
        Body(
            ...,
            description="JSON object containing username and password",
        ),
    ],
):
    auth_type = login_details.auth_type

    login_details.sha256_password = User.check_and_hash(login_details.sha256_password)

    if auth_type not in User.auth_type_list:
        log.error("auth_type was not 'local' or 'FedID'")
        raise QueryParameterError(
            f"auth_type must be either 'local' or 'FedID'. You put: '{auth_type}' ",
        )

    if auth_type == "FedID" and login_details.sha256_password:
        log.error("no password is required for the auth_type input (FedID)")
        raise QueryParameterError(
            "for the auth_type you put (FedID), no password is required."
            " Please remove this field",
        )

    if auth_type == "local" and login_details.sha256_password is None:
        log.error("a password is required for the auth_type input (local)")
        raise QueryParameterError(
            "for the auth_type you put (local), a password is required."
            " Please add this field",
        )

    User.check_routes(login_details.authorised_routes)

    if login_details.username == "":
        log.error("username must not be empty")
        raise QueryParameterError(
            "username field must not be filled"
            f". You put: '{login_details.username}' ",
        )

    try:
        await User.get_user(login_details.username)
        log.error("username must be unique")
        raise QueryParameterError(
            "username field must not be the same as a pre existing"
            f" user. You put: '{login_details.username}' ",
        )
    except UnauthorisedError:
        log.info("username is not duplicated.")
        # if an UnauthorisedError is raised, then the
        # username is not duplicated so can continue
        pass

    await User.add(login_details)

    log.info("successfully created user '%s' ", login_details.username)

    return JSONResponse(
        login_details.username,
        status_code=status.HTTP_201_CREATED,
    )


@router.patch(
    "/users",
    summary="Update a user’s authorised routes.",
    response_description="Confirmation that the user's path authority"
    " has been successfully updated",
    tags=["Users"],
)
@endpoint_error_handling
async def update_user(
    access_token: AuthoriseRoute,
    change_details: Annotated[
        UpdateUserModel,
        Body(
            ...,
            description="JSON object containing username, password to change,"
            " routes to delete and routes to add",
        ),
    ],
):
    change_details.updated_password = User.check_and_hash(
        change_details.updated_password
    )

    User.check_routes(change_details.add_authorised_routes)

    User.check_routes(change_details.remove_authorised_routes)

    user = await User.check_username_exists(change_details.username)

    if user.auth_type == "local":
        await User.update_password(
            change_details.username,
            change_details.updated_password,
        )
    else:
        log.info("cannot add password to FedID user type")

    await User.edit_routes(
        change_details.username,
        user.authorised_routes,
        change_details.add_authorised_routes,
    )

    user = await User.get_user(change_details.username)

    await User.edit_routes(
        change_details.username,
        user.authorised_routes,
        change_details.remove_authorised_routes,
        add=False,
    )

    return f"Updated {change_details.username}"


@router.delete(
    "/users/{id_}",
    summary="Delete a user by specifying their ID",
    response_description="No content",
    status_code=204,
    tags=["Users"],
)
@endpoint_error_handling
async def delete_user(
    id_: Annotated[
        str,
        Path(
            ...,
            description="`_id` (username) of the user to remove from the database",
        ),
    ],
    access_token: AuthoriseRoute,
):
    try:
        await User.get_user(id_)
    except UnauthorisedError as err:
        log.error("username field did not exist in the database")
        raise QueryParameterError(
            f"username field must exist in the database. You put: '{id_}'",
        ) from err

    await User.delete(id_)

    log.info("successfully deleted user '%s' ", id_)

    return Response(status_code=HTTPStatus.NO_CONTENT.value)
