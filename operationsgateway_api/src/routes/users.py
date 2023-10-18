import logging

from fastapi import APIRouter, Depends, Body, Path
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
        log.error(f"auth_type must be either 'local' or 'FedID'. You put: {auth_type}")
        # TODO suitable error message
        
    if _id == "":
        log.error(f"username field must exist and must not already be present in the database. You put: {_id}")
        
    # TODO check if the _id (username) already exists
    
    # TODO check if required things exist
    
    # TODO check if the password is correct if not None
    
    # TODO check if authrised_routes is correct if not None
    
    log.info(login_details)
    log.info(login_details.username)
    log.info(login_details.auth_type)
    log.info(login_details.sha256_password)
    log.info(login_details.authorised_routes)

    # TODO create user directly in database (includes first 2, other 2 only if not None)
    
    # TODO on failure suitable error message why
    
    # TODO on success make suitable log message




@router.patch(
    "/users",
    summary="Update a user’s authorised routes.",
    response_description="NEED TO CHANGE",################## TODO
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





@router.delete(
    "/users/{id_}",
    summary="Delete a user by specifying their ID",
    response_description="NEED TO CHANGE",################## TODO
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





# TODO user password update?