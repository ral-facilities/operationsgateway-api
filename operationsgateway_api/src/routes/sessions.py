from datetime import datetime
from http import HTTPStatus
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends, Path, Query, Response, status
from fastapi.responses import JSONResponse

from operationsgateway_api.src.auth.authorisation import authorise_token
from operationsgateway_api.src.auth.jwt_handler import JwtHandler
from operationsgateway_api.src.constants import DATA_DATETIME_FORMAT
from operationsgateway_api.src.error_handling import endpoint_error_handling
from operationsgateway_api.src.models import UserSessionModel
from operationsgateway_api.src.sessions.user_session import UserSession
from operationsgateway_api.src.sessions.user_session_list import UserSessionList


log = logging.getLogger()
router = APIRouter()


@router.get(
    "/sessions/list",
    summary="Get a list of session names that belong to the given user",
    response_description="List of session names",
    tags=["Sessions"],
)
@endpoint_error_handling
async def get_user_sessions_list(
    access_token: str = Depends(authorise_token),
):
    """
    Get a list of user sessions that belong to the current user and respond with the
    sessions' metadata
    """

    token_payload = JwtHandler.get_payload(access_token)
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
    # TODO - what happens if the ID contains /? Same for DELETE endpoint
    id_: str = Path(
        ...,
        description="`_id` of the user session to fetch from the database",
    ),
    access_token: str = Depends(authorise_token),
):
    """
    Get a single user session by its ID and return it as a JSON response
    """

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
    id_: str = Path(
        ...,
        description="`_id` of the user session to remove from the database",
    ),
    access_token: str = Depends(authorise_token),
):
    """
    Delete a user session given its ID. A check is performed to ensure sessions can only
    be deleted by the users who create them. This should prevent cases where a user X
    could delete the user session of user Y
    """

    await UserSession.delete(id_, access_token)
    return Response(status_code=HTTPStatus.NO_CONTENT.value)


@router.put(
    "/sessions",
    summary="Store a session into the database",
    response_description="ID of the user session that's been inserted/updated",
    tags=["Sessions"],
)
@endpoint_error_handling
async def save_user_session(
    data: Dict[str, Any] = Body(...),
    name: str = Query(
        "",
        description="Name of the user session",
    ),
    summary: Optional[str] = Query(
        None,
        description="Summary of the user session",
    ),
    auto_saved: bool = Query(
        description="Flag to show whether the session has been manually or"
        " automatically saved",
    ),
    access_token: str = Depends(authorise_token),
):
    """
    Save/update a user session (and its metadata) into the database
    """

    log.debug("Name: %s, Summary: %s", name, summary)
    log.debug("Data: %s", data)

    token_payload = JwtHandler.get_payload(access_token)
    username = token_payload["username"]

    session_data = UserSessionModel(
        _id=f"{username}_{name}",
        username=username,
        name=name,
        summary=summary,
        auto_saved=auto_saved,
        timestamp=datetime.strftime(datetime.now(), DATA_DATETIME_FORMAT),
        session=data,
    )

    log.debug("Session: %s", session_data)

    user_session = UserSession(session_data)
    inserted = await user_session.upsert()

    if inserted:
        return JSONResponse(
            str(user_session.session.id_),
            status_code=status.HTTP_201_CREATED,
            headers={"Location": f"/sessions/{user_session.session.id_}"},
        )
    else:
        return f"Updated {user_session.session.id_}"
