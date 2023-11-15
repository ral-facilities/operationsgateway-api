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

    if login_details.sha256_password is not None:
        if login_details.sha256_password == "":
            raise QueryParameterError("you must input a password")
        else:
            login_details.sha256_password = User.hash_password(
                login_details.sha256_password,
            )

    if auth_type != "local" and auth_type != "FedID":
        log.error("auth_type was not 'local' or 'FedID'")
        raise QueryParameterError(
            f"auth_type must be either 'local' or 'FedID'. You put: '{auth_type}' ",
        )

    if auth_type == "FedID" and login_details.sha256_password is not None:
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

    if login_details.authorised_routes is not None:
        invalid_routes = User.check_authorised_routes(login_details.authorised_routes)
        if invalid_routes:
            log.error("some of the authorised routes entered were invalid")
            raise QueryParameterError(
                f"some of the routes entered are invalid:  {invalid_routes} ",
            )

    try:
        if login_details.username == "":
            log.error("username must not be empty")
            raise QueryParameterError(
                "username field must not be filled"
                f". You put: '{login_details.username}' ",
            )
        await User.get_user(login_details.username)
        log.error("username must be unique")
        raise QueryParameterError(
            "username field must not be the same as a pre existing"
            f" user. You put: '{login_details.username}' ",
        )
    except UnauthorisedError:
        pass

    await MongoDBInterface.insert_one(
        "users",
        login_details.model_dump(by_alias=True, exclude_unset=True),
    )
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
    if change_details.updated_password is not None:
        if change_details.updated_password == "":
            raise QueryParameterError(
                "you must have a password with the password field",
            )
        else:
            change_details.updated_password = User.hash_password(
                change_details.updated_password,
            )

    if change_details.add_authorised_routes is not None:
        invalid_routes = User.check_authorised_routes(
            change_details.add_authorised_routes,
        )
        if invalid_routes:
            log.error("some of the authorised routes to add entered were invalid")
            raise QueryParameterError(
                f"some of the routes entered are invalid:  {invalid_routes} ",
            )

    if change_details.remove_authorised_routes is not None:
        invalid_routes = User.check_authorised_routes(
            change_details.remove_authorised_routes,
        )
        if invalid_routes:
            log.error("some of the authorised routes to remove entered were invalid")
            raise QueryParameterError(
                f"some of the routes entered are invalid:  {invalid_routes} ",
            )

    try:
        if change_details.username == "":
            raise ValueError
        user = await User.get_user(change_details.username)
    except (UnauthorisedError, ValueError) as err:
        log.error("username field did not exist in the database, _id is required")
        raise QueryParameterError() from err

    if user.auth_type == "local":
        await MongoDBInterface.update_one(
            "users",
            filter_={"_id": change_details.username},
            update={"$set": {"sha256_password": change_details.updated_password}},
        )
    else:
        log.info("cannot add password to FedID user type")

    if change_details.add_authorised_routes is not None:
        if user.authorised_routes is not None:
            change_details.add_authorised_routes = user.authorised_routes + list(
                set(change_details.add_authorised_routes) - set(user.authorised_routes),
            )
        await MongoDBInterface.update_one(
            "users",
            filter_={"_id": change_details.username},
            update={
                "$set": {"authorised_routes": change_details.add_authorised_routes},
            },
        )

    user = await User.get_user(change_details.username)
    if change_details.remove_authorised_routes is not None:
        if user.authorised_routes is not None:
            change_details.remove_authorised_routes = list(
                set(user.authorised_routes)
                - set(change_details.remove_authorised_routes),
            )
        await MongoDBInterface.update_one(
            "users",
            filter_={"_id": change_details.username},
            update={
                "$set": {"authorised_routes": change_details.remove_authorised_routes},
            },
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

    await MongoDBInterface.delete_one(
        "users",
        filter_={"_id": id_},
    )
    log.info("successfully deleted user '%s' ", id_)

    return Response(status_code=HTTPStatus.NO_CONTENT.value)
