from hashlib import sha256
from http import HTTPStatus
import logging

from fastapi import APIRouter, Body, Depends, Path, Response, status
from fastapi.responses import JSONResponse
from typing_extensions import Annotated

from operationsgateway_api.src.auth.authorisation import authorise_route
from operationsgateway_api.src.error_handling import endpoint_error_handling
from operationsgateway_api.src.exceptions import DatabaseError, QueryParameterError
from operationsgateway_api.src.models import UserModel
from operationsgateway_api.src.mongo.interface import MongoDBInterface

log = logging.getLogger()
router = APIRouter()
AuthoriseRoute = Annotated[str, Depends(authorise_route)]


def check_authorised_routes(authorised_route):
    authorised_route_list = [
        "/submit/hdf POST",
        "/submit/manifest POST",
        "/records/{id_} DELETE",
        "/experiments POST",
        "/users POST",
        "/users PATCH",
        "/users/{id_} DELETE",
    ]
    difference = list(set(authorised_route) - set(authorised_route_list))
    return difference


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
    _id = login_details.username

    if login_details.sha256_password is not None:
        if login_details.sha256_password == "":
            raise QueryParameterError("you must input a password")
        else:
            sha_256 = sha256()
            sha_256.update(login_details.sha256_password.encode())
            login_details.sha256_password = sha_256.hexdigest()

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
        invalid_routes = check_authorised_routes(login_details.authorised_routes)
        if invalid_routes:
            log.error("some of the authorised routes entered were invalid")
            raise QueryParameterError(
                f"some of the routes entered are invalid:  {invalid_routes} ",
            )

    if (
        await MongoDBInterface.find_one(
            "users",
            filter_={"_id": login_details.username},
        )
        is not None
        or _id == ""
    ):
        log.error("username must be unique and not empty")
        raise DatabaseError(
            "username field must not be the same as a pre existing"
            f" user or empty. You put: '{login_details.username}' ",
        )

    insert_result = await MongoDBInterface.insert_one(
        "users",
        login_details.model_dump(by_alias=True, exclude_unset=True),
    )
    log.debug("id_ of inserted session: %s", insert_result.inserted_id)
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
async def update_user_authority(
    access_token: AuthoriseRoute,
):
    # TODO get correct user from database (using id?)

    # TODO update the user's authorised_routes

    # TODO on failure make suitable error message

    # TODO on success make suitable log message

    pass
    # return f"Updated {HERE WILL BE THE USERNAME OF THE CHANGED USER}"


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
    if (
        await MongoDBInterface.find_one(
            "users",
            filter_={"_id": id_},
        )
        is None
    ):
        log.error("username field did not exist in the database")
        raise DatabaseError(
            f"username field must exist in the database. You put: '{id_}'",
        )

    await MongoDBInterface.delete_one(
        "users",
        filter_={"_id": id_},
    )
    log.info("successfully deleted user '%s' ", id_)

    return Response(status_code=HTTPStatus.NO_CONTENT.value)


# TODO user password update?
