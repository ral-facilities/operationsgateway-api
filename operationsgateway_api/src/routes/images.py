import logging

from fastapi import APIRouter, Path, Query
from fastapi.responses import FileResponse

from operationsgateway_api.src.records.image import Image

log = logging.getLogger()
router = APIRouter()


@router.get(
    "/images/{record_id}/{channel_name}",
    summary="Get full-size image from disk",
    response_description="Image in .png format or base64 encoded string of the image",
    tags=["Images"],
)
async def get_full_image(
    record_id: str = Path(  # noqa: B008
        "",
        description="ID of the record (usually timestamp)",
        examples={
            "test_data": {
                "summary": "Example record ID number",
                "value": "20220408132830",
            },
        },
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
        return Image.get_image(record_id, channel_name)
    else:
        return FileResponse(Image.get_image_path(record_id, channel_name))
