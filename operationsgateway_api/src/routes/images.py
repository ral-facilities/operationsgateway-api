import logging

from fastapi import APIRouter

log = logging.getLogger()
router = APIRouter()


@router.get("/images/{shot_id}/{channel_name}", response_description="")
async def get_full_image(shot_id: str, channel_name: str):
    pass
