from http import HTTPStatus
import logging

from fastapi import APIRouter, Depends, Path, Query, Response, status
from fastapi.responses import JSONResponse
from typing_extensions import Annotated

from operationsgateway_api.src.auth.authorisation import authorise_token
from operationsgateway_api.src.auth.jwt_handler import JwtHandler
from operationsgateway_api.src.error_handling import endpoint_error_handling
from operationsgateway_api.src.users.favourite_filter import FavouriteFilter


log = logging.getLogger()
router = APIRouter()
AuthoriseToken = Annotated[str, Depends(authorise_token)]


@router.get(
    "/users/filters",
    summary="Get a list of the user's favourite filters",
    response_description="List of favourite filters",
    tags=["Filters"],
)
@endpoint_error_handling
async def get_favourite_filters(access_token: AuthoriseToken):
    """
    Get a list of the user's favourite filters that belong to the user sending the
    request
    """

    token_payload = JwtHandler.get_payload(access_token)
    username = token_payload["username"]
    log.info("Getting favourite filters for user %s", username)

    return await FavouriteFilter.get_list(username)


@router.get(
    "/users/filters/{_id}",
    summary="Get a specific favourite filter",
    response_description="Specific favourite filter",
    tags=["Filters"],
)
@endpoint_error_handling
async def get_favourite_filter_by_id(
    _id: Annotated[
        str,
        Path(
            ...,
            description="`_id` of the filter to get",
        ),
    ],
    access_token: AuthoriseToken,
):
    """
    Get a specific favourite filter given its ID
    """

    token_payload = JwtHandler.get_payload(access_token)
    username = token_payload["username"]
    log.info("Getting favourite filter of _id '%s' for user '%s'", _id, username)
    return await FavouriteFilter.get_by_id(username, _id)


@router.post(
    "/users/filters",
    summary="Store a favourite filter into the user's document in the database",
    response_description="The favourite filter id",
    tags=["Filters"],
)
@endpoint_error_handling
async def create_favourite_filter(
    access_token: AuthoriseToken,
    name: str = Query(
        "",
        description="Name of the favourite filter",
    ),
    filter: str = Query(  # noqa: A002
        "",
        description="Contents of the favourite filter",
    ),
):
    """
    Create a favourite filter for the user sending the request and save it in the user's
    document in the database
    """

    token_payload = JwtHandler.get_payload(access_token)
    username = token_payload["username"]

    log.info("Creating favourite filter for user '%s'", username)
    new_filter = FavouriteFilter(username, name, filter)
    filter_id = await new_filter.create()

    return JSONResponse(
        str(filter_id),
        status_code=status.HTTP_201_CREATED,
        headers={"Location": f"/users/filters/{filter_id}"},
    )


@router.patch(
    "/users/filters/{_id}",
    summary="Update a user's favourite filter",
    response_description="Confirmation that the filter has been successfully updated",
    tags=["Filters"],
)
@endpoint_error_handling
async def update_favourite_filter(
    access_token: AuthoriseToken,
    _id: Annotated[
        str,
        Path(
            ...,
            description="`_id` of the favourite filter to update",
        ),
    ],
    name: str = Query(
        "",
        description="Name of the favourite filter",
    ),
    filter: str = Query(  # noqa: A002
        "",
        description="Contents of the favourite filter",
    ),
):
    """
    Update a user's favourite filter (including its name) given its ID as a path
    parameter
    """

    token_payload = JwtHandler.get_payload(access_token)
    username = token_payload["username"]

    log.info("Updating favourite filter '%s' for user '%s", _id, username)
    log.debug("Name: %s, Filter: %s", name, filter)

    update_filter = FavouriteFilter(
        username,
        name,
        filter,
        id_=_id,
    )

    await update_filter.update()
    return f"Updated {_id}"


@router.delete(
    "/users/filters/{_id}",
    summary="Delete a favourite filter",
    response_description="No content",
    status_code=204,
    tags=["Filters"],
)
@endpoint_error_handling
async def delete_favourite_filter(
    _id: Annotated[
        str,
        Path(
            ...,
            description="`_id` of the filter to remove from the database",
        ),
    ],
    access_token: AuthoriseToken,
):
    """
    Delete a user's favourite filter given its ID
    """

    token_payload = JwtHandler.get_payload(access_token)
    username = token_payload["username"]

    await FavouriteFilter.delete(username, _id)
    return Response(status_code=HTTPStatus.NO_CONTENT.value)
