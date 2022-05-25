import logging

from fastapi import APIRouter

from operationsgateway_api.src.data_encoding import DataEncoding
from operationsgateway_api.src.models import Record

from operationsgateway_api.src.mongo.interface import MongoDBInterface


log = logging.getLogger()
router = APIRouter()


@router.get("/waveforms/{id_}", response_description="")
async def get_waveform_by_id(id_: str):
    log.info("Getting waveform by ID: %s", id_)

    waveform = await MongoDBInterface.find_one(
        "waveforms",
        {"_id": DataEncoding.encode_object_id(id_)},
    )

    # TODO - need to make that model more generic, not specific to records
    return Record.construct(waveform.keys(), **waveform)
