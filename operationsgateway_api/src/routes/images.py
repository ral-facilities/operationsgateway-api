import logging
from typing import Optional

from fastapi import APIRouter, Depends, Path, Query
from fastapi.responses import StreamingResponse

from operationsgateway_api.src.auth.authorisation import authorise_token
from operationsgateway_api.src.error_handling import endpoint_error_handling
from operationsgateway_api.src.records.false_colour_handler import FalseColourHandler
from operationsgateway_api.src.records.image import Image

log = logging.getLogger()
router = APIRouter()


@router.get(
    "/images/{record_id}/{channel_name}",
    summary="Get full-size image from disk",
    response_description="Image in .png format",
    tags=["Images"],
)
@endpoint_error_handling
async def get_full_image(
    record_id: str,
    channel_name: str,
    original_image: Optional[bool] = Query(
        False,
        description="Return the original image in PNG format without any false colour"
        " applied (false)",
    ),
    lower_level: Optional[int] = Query(
        0,
        description="The lower level threshold for false colour (0-255)",
        ge=0,
        le=255,
    ),
    upper_level: Optional[int] = Query(
        255,
        description="The upper level threshold for false colour (0-255)",
        ge=0,
        le=255,
    ),
    colourmap_name: Optional[str] = Query(
        None,
        description="The name of the matplotlib colour map to apply",
    ),
    access_token: str = Depends(authorise_token),
):
    """
    This endpoint can be used to retrieve a full-size image by specifying the shot
    number and channel name. Images are stored on disk and can be returned as a .png
    file, by default with false colour applied or optionally as the original image by
    setting 'original_image' to True
    """

    image_bytes = await Image.get_image(
        record_id,
        channel_name,
        original_image,
        lower_level,
        upper_level,
        colourmap_name,
    )
    # ensure the "file pointer" is reset
    image_bytes.seek(0)
    return StreamingResponse(image_bytes, media_type="image/png")


@router.get(
    "/images/colour_bar",
    summary="Get a colourbar image",
    response_description="Image in .png format",
    tags=["Images"],
)
@endpoint_error_handling
async def get_colourbar_image(
    lower_level: Optional[int] = Query(
        0,
        description="The lower level threshold for false colour (0-255)",
        ge=0,
        le=255,
    ),
    upper_level: Optional[int] = Query(
        255,
        description="The upper level threshold for false colour (0-255)",
        ge=0,
        le=255,
    ),
    colourmap_name: Optional[str] = Query(
        None,
        description="The name of the matplotlib colour map to apply",
    ),
    access_token: str = Depends(authorise_token),
):
    """
    This endpoint can be used to retrieve a colourbar image showing the colour spectrum
    for the specified colour map with the upper and lower limits set. If either limit
    is not specified then the default of 0 for the lower level and/or 255 for the upper
    level will be used.
    """
    colourbar_image_bytes = FalseColourHandler.create_colourbar(
        lower_level,
        upper_level,
        colourmap_name,
    )
    colourbar_image_bytes.seek(0)
    return StreamingResponse(colourbar_image_bytes, media_type="image/png")


@router.get(
    "/images/colourmap_names",
    summary="Get a list of the available colourmaps",
    response_description="A list of available colourmaps in alphabetical order and"
    " including the reverse (_r) versions of each map",
    tags=["Images"],
)
@endpoint_error_handling
async def get_colourmap_names(
    access_token: str = Depends(authorise_token),
):
    """
    This endpoint returns an ordered dictionary of the colourmap names (grouped into a
    number of categories) that can be used in various API calls. They are those
    available in matplotlib and more detail is at:
    https://matplotlib.org/stable/gallery/color/colormap_reference.html.
    Those with '_r' appended to them are the reversed versions of the colourmap with
    the same name. This is also explained on the matplotlib page.
    """
    return FalseColourHandler.colourmap_names
