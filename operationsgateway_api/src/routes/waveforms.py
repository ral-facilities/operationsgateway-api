import logging

from fastapi import APIRouter, Path

from operationsgateway_api.src.data_encoding import DataEncoding
from operationsgateway_api.src.models import Record
from operationsgateway_api.src.mongo.interface import MongoDBInterface


log = logging.getLogger()
router = APIRouter()


@router.get(
    "/waveforms/{id_}",
    summary="Get a waveform object specified by its ID",
    response_description="Single waveform object",
    tags=["Waveforms"],
)
async def get_waveform_by_id(
    id_: str = Path(  # noqa: B008
        ...,
        description="`_id` of the waveform to fetch from MongoDB",
    ),
):
    """
    This endpoint gets a single waveform object by specifying its ID. You can find the
    ID of a waveform object by finding the `waveform_id` field on a waveform channel in
    a record object. `waveform_id` is simply a reference to a waveform which is stored
    in a different collection/table
    """

    log.info("Getting waveform by ID: %s", id_)

    waveform = await MongoDBInterface.find_one(
        "waveforms",
        {"_id": DataEncoding.encode_object_id(id_)},
    )

    # TODO - need to make that model more generic, not specific to records. Or make a
    # separate model probably
    return Record.construct(waveform.keys(), **waveform)
