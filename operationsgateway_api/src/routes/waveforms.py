import logging

from fastapi import APIRouter, Depends, Path

from operationsgateway_api.src.auth.authorisation import authorise_token
from operationsgateway_api.src.models import Record
from operationsgateway_api.src.mongo.interface import MongoDBInterface


log = logging.getLogger()
router = APIRouter()


@router.get(
    "/waveforms/{record_id}/{channel_name}",
    summary="Get a waveform object, specified by record ID and channel name",
    response_description="Single waveform object",
    tags=["Waveforms"],
)
async def get_waveform_by_id(
    record_id: str = Path(  # noqa: B008
        "",
        description="ID of the record (usually timestamp)",
        examples={
            "test_data": {
                "summary": "Example record ID number",
                "value": "20220408140310",
            },
        },
    ),
    channel_name: str = Path(  # noqa: B008
        "",
        description="Channel name containing the waveform",
        examples={
            "test_data": {
                "summary": "Example waveform channel name",
                "value": "N_COMP_SPEC_TRACE",
            },
        },
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

    waveform = await MongoDBInterface.find_one(
        "waveforms",
        {"_id": waveform_id},
    )

    # TODO - need to make that model more generic, not specific to records. Or make a
    # separate model probably
    return Record.construct(waveform.keys(), **waveform)
