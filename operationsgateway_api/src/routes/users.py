from http import HTTPStatus
import logging

from fastapi import APIRouter, Body, Depends, Path, Response, status
from fastapi.responses import JSONResponse
from typing_extensions import Annotated

from operationsgateway_api.src.auth.authorisation import authorise_route
from operationsgateway_api.src.error_handling import endpoint_error_handling
from operationsgateway_api.src.models import UserModel

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
    _id = login_details.username

    if auth_type != "local" and auth_type != "FedID":
        log.error(
            "auth_type must be either 'local' or 'FedID'. You put: '%s' ",
            auth_type,
        )
        # TODO suitable error message

    if _id == "":
        log.error("username field must not be empty")
        # TODO suitable error message

    # TODO check if the _id (username) already exists
    # (just query the database and try catch the error)

    # TODO check if required things exist

    # TODO check if the password exists if the type is local
    # and if it is None if its Fed

    # TODO check if authrised_routes is correct if not None

    log.info(login_details)
    log.info(login_details.username)
    log.info(login_details.auth_type)
    log.info(login_details.sha256_password)
    log.info(login_details.authorised_routes)

    # TODO create user directly in database (includes first 2, other 2 only if not None)

    # TODO on failure suitable error message why

    # TODO on success make suitable log message

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
    log.info(id_)

    # TODO find the id of the thing in the database and delete it

    # TODO if no id exists create suitable error message

    # TODO on success create suitable log message

    return Response(status_code=HTTPStatus.NO_CONTENT.value)


# TODO user password update?
