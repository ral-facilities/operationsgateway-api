import logging

from fastapi import APIRouter, Depends, Path

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
    record_id: str = Path(  # noqa: B008
        "",
        description="ID of the record (usually timestamp)",
    ),
    channel_name: str = Path(  # noqa: B008
        "",
        description="Channel name containing the waveform",
    ),
    access_token: str = Depends(authorise_token),  # noqa: B008
):
    """
    This endpoint gets a single waveform object by channel name and the record ID that
    the waveform belongs to. These two pieces of data form the waveform ID. You can find
    the ID of a waveform object by finding the `waveform_id` field on a waveform channel
    in a record object. `waveform_id` is simply a reference to a waveform which is
    stored in a different collection/table
    """

    waveform_id = f"{record_id}_{channel_name}"

    log.info("Getting waveform by ID: %s", waveform_id)

    return await Waveform.get_waveform(waveform_id)
