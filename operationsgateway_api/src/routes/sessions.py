from datetime import datetime
from http import HTTPStatus
import logging
from typing import Any, Dict, Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Body, Depends, Path, Query, Response, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from typing_extensions import Annotated

from operationsgateway_api.src.auth.authorisation import authorise_token
from operationsgateway_api.src.auth.jwt_handler import JwtHandler
from operationsgateway_api.src.constants import SESSION_DATETIME_FORMAT
from operationsgateway_api.src.error_handling import endpoint_error_handling
from operationsgateway_api.src.exceptions import ModelError
from operationsgateway_api.src.models import UserSessionModel
from operationsgateway_api.src.sessions.user_session import UserSession
from operationsgateway_api.src.sessions.user_session_list import UserSessionList


log = logging.getLogger()
router = APIRouter()
AuthoriseToken = Annotated[str, Depends(authorise_token)]


@router.get(
    "/sessions/list",
    summary="Get a list of sessions (metadata only, not the actual session data)"
    " that belong to the given user",
    response_description="List of session names",
    tags=["Sessions"],
)
@endpoint_error_handling
async def get_user_sessions_list(
    access_token: AuthoriseToken,
):
    """
    Get a list of user sessions that belong to the current user and respond with the
    sessions' metadata
    """

    token_payload = JwtHandler.get_payload(access_token)
    log.info(
        "Getting list of user session metadata for user '%s'",
        token_payload["username"],
    )
    user_sessions_list = UserSessionList(token_payload["username"])
    return await user_sessions_list.get_session_list()


@router.get(
    "/sessions/{id_}",
    summary="Retrieve a specific session",
    response_description="User session, including its metadata",
    tags=["Sessions"],
)
@endpoint_error_handling
async def get_user_session(
    id_: Annotated[
        str,
        Path(
            ...,
            description="`_id` of the user session to fetch from the database",
        ),
    ],
    access_token: AuthoriseToken,
):
    """
    Get a single user session by its ID and return it as a JSON response
    """

    log.info("Getting user session: %s", id_)
    return await UserSession.get(id_)


@router.delete(
    "/sessions/{id_}",
    summary="Delete a specific session",
    response_description="No content",
    status_code=204,
    tags=["Sessions"],
)
@endpoint_error_handling
async def delete_user_session(
    id_: Annotated[
        str,
        Path(
            ...,
            description="`_id` of the user session to remove from the database",
        ),
    ],
    access_token: AuthoriseToken,
):
    """
    Delete a user session given its ID. A check is performed to ensure sessions can only
    be deleted by the users who create them. This should prevent cases where a user X
    could delete the user session of user Y
    """

    log.info("Request to delete user session: %s", id_)
    await UserSession.delete(id_, access_token)
    return Response(status_code=HTTPStatus.NO_CONTENT.value)


@router.post(
    "/sessions",
    summary="Store a session into the database",
    response_description="ID of the user session that's been inserted/updated",
    tags=["Sessions"],
)
@endpoint_error_handling
async def save_user_session(
    data: Annotated[Dict[str, Any], Body(...)],
    auto_saved: Annotated[
        bool,
        Query(
            description="Flag to show whether the session has been manually or"
            " automatically saved",
        ),
    ],
    access_token: AuthoriseToken,
    name: str = Query(
        "",
        description="Name of the user session",
    ),
    summary: Optional[str] = Query(
        None,
        description="Summary of the user session",
    ),
):
    """
    Save/update a user session (and its metadata) into the database
    """

    token_payload = JwtHandler.get_payload(access_token)
    username = token_payload["username"]

    log.info(
        "Saving user session for user '%s'. Session name: %s, auto saved: %s,"
        " summary: %s",
        username,
        name,
        auto_saved,
        summary,
    )

    session_data = UserSessionModel(
        username=username,
        name=name,
        summary=summary,
        auto_saved=auto_saved,
        timestamp=datetime.strftime(datetime.now(), SESSION_DATETIME_FORMAT),
        session=data,
    )

    user_session = UserSession(session_data)
    inserted_id = await user_session.insert()

    return JSONResponse(
        str(inserted_id),
        status_code=status.HTTP_201_CREATED,
        headers={"Location": f"/sessions/{inserted_id}"},
    )


@router.patch(
    "/sessions/{id_}",
    summary="Update a session given its ID",
    response_description="Confirmation that the user session has been successfully"
    "updated",
    tags=["Sessions"],
)
@endpoint_error_handling
async def update_user_session(
    id_: Annotated[
        str,
        Path(
            ...,
            description="`_id` of the user session to remove from the database",
        ),
    ],
    data: Annotated[Dict[str, Any], Body(...)],
    auto_saved: Annotated[
        bool,
        Query(
            description="Flag to show whether the session has been manually or"
            " automatically saved",
        ),
    ],
    access_token: AuthoriseToken,
    name: str = Query(
        "",
        description="Name of the user session",
    ),
    summary: Optional[str] = Query(
        None,
        description="Summary of the user session",
    ),
):
    """
    Update a user session (and its metadata) given its ID as a path parameter
    """

    log.info("Updating user session: %s", id_)

    token_payload = JwtHandler.get_payload(access_token)
    username = token_payload["username"]

    try:
        session_data = UserSessionModel(
            _id=ObjectId(id_),
            username=username,
            name=name,
            summary=summary,
            auto_saved=auto_saved,
            timestamp=datetime.strftime(datetime.now(), SESSION_DATETIME_FORMAT),
            session=data,
        )
    except ValidationError as exc:
        raise ModelError(str(exc)) from exc
    except InvalidId as exc:
        raise ModelError("ID provided is not a valid ObjectId") from exc

    user_session = UserSession(session_data)

    await user_session.update(access_token)
    return f"Updated {user_session.session.id_}"
