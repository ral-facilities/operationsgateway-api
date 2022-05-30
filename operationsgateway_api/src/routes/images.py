import base64
import logging

from fastapi import APIRouter
from fastapi.responses import FileResponse

from operationsgateway_api.src.config import Config

log = logging.getLogger()
router = APIRouter()


@router.get("/images/{shot_num}/{channel_name}", response_description="")
async def get_full_image(
    shot_num: str,
    channel_name: str,
    string_response: bool = False,
):
    if string_response:
        with open(
            f"{Config.config.mongodb.image_store_directory}/{shot_num}_{channel_name}"
            ".png",
            "rb",
        ) as image:
            image_string = base64.b64encode(image.read())
        return image_string
    else:
        return FileResponse(
            f"{Config.config.mongodb.image_store_directory}/{shot_num}_{channel_name}"
            ".png",
        )
