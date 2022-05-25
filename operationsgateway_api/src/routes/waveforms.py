import logging

from fastapi import APIRouter


log = logging.getLogger()
router = APIRouter()


@router.get("/waveforms/{id_}", response_description="")
async def get_waveform_by_id(id_: str):
    pass

# TODO - do we want /waveforms/count