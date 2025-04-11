import logging

from fastapi import APIRouter, Depends, Path
from typing_extensions import Annotated


from operationsgateway_api.src.auth.authorisation import authorise_token
from operationsgateway_api.src.error_handling import endpoint_error_handling
from operationsgateway_api.src.records.vector import Vector


log = logging.getLogger()
router = APIRouter()


@router.get(
    "/vectors/{record_id}/{channel_name}",
    summary="Get a vector object, specified by record ID and channel name",
    response_description="Single vector object",
    tags=["Vectors"],
)
@endpoint_error_handling
async def get_vector_by_id(
    record_id: Annotated[
        str,
        Path(
            ...,
            description="ID of the record (usually timestamp)",
        ),
    ],
    channel_name: Annotated[
        str,
        Path(
            ...,
            description="Channel name containing the vector",
        ),
    ],
    access_token: Annotated[str, Depends(authorise_token)],
):
    """
    This endpoint gets a single vector object by channel name and the record ID that
    the vector belongs to.
    """
    msg = "Getting vector by record_id, channel_name: %s, %s"
    log.info(msg, record_id, channel_name)
    return await Vector.get_vector(record_id, channel_name)
