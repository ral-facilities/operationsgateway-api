import base64
import logging

from fastapi import APIRouter, Path, Query
from fastapi.responses import FileResponse

from operationsgateway_api.src.config import Config

log = logging.getLogger()
router = APIRouter()


@router.get(
    "/images/{shot_num}/{channel_name}",
    summary="Get full-size image from disk",
    response_description="Image in .png format or base64 encoded string of the image",
    tags=["Images"],
)
async def get_full_image(
    shot_num: str = Path(  # noqa: B008
        "",
        description="Shot number of the record",
        examples={"test_data": {"summary": "Example shot number", "value": 366368}},
    ),
    channel_name: str = Path(  # noqa: B008
        "",
        description="Channel name containing the image",
        examples={
            "test_data": {
                "summary": "Example image channel name",
                "value": "N_COMP_FF_IMAGE",
            },
        },
    ),
    string_response: bool = Query(  # noqa: B008
        False,
        description="Return image as a base64 encoded string (true) or as a .png file"
        " (false)",
    ),
):
    """
    This endpoint can be used to retrieve a full-size image by specifying the shot
    number and channel name. Images are stored on disk and can be returned as a base64
    encoded string of the image or as a .png file, by toggling `string_response`
    """

    if string_response:
        with open(
            f"{Config.config.mongodb.image_store_directory}/{shot_num}/{channel_name}"
            ".png",
            "rb",
        ) as image_file:
            image_string = base64.b64encode(image_file.read())
        return image_string
    else:
        return FileResponse(
            f"{Config.config.mongodb.image_store_directory}/{shot_num}/{channel_name}"
            ".png",
        )
