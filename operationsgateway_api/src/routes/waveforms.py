import logging

from fastapi import APIRouter, Depends, Path
from typing_extensions import Annotated

from operationsgateway_api.src.auth.authorisation import authorise_token
from operationsgateway_api.src.error_handling import endpoint_error_handling
from operationsgateway_api.src.records.waveform import Waveform


log = logging.getLogger()
router = APIRouter()


@router.get(
    "/waveforms/{record_id}/{channel_name}",
    summary="Get a waveform object, specified by record ID and channel name",
    response_description="Single waveform object",
    tags=["Waveforms"],
)
@endpoint_error_handling
async def get_waveform_by_id(
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
            description="Channel name containing the waveform",
        ),
    ],
    access_token: Annotated[str, Depends(authorise_token)],
):
    """
    This endpoint gets a single waveform object by channel name and the record ID that
    the waveform belongs to. These two pieces of data form the waveform ID. You can find
    the ID of a waveform object by finding the `waveform_id` field on a waveform channel
    in a record object. `waveform_id` is simply a reference to a waveform which is
    stored in a different collection/table
    """

    waveform_path = Waveform.get_relative_path(record_id, channel_name)
    log.info("Getting waveform by path: %s", waveform_path)
    return Waveform.get_waveform(waveform_path)
