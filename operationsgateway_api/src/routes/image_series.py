from io import BytesIO
from typing import Optional

from fastapi import APIRouter, Depends, Query, Response
import numpy as np
from PIL import Image as PILImage
from pydantic import Json, NonNegativeInt
from typing_extensions import Annotated

from operationsgateway_api.src.auth.authorisation import authorise_token
from operationsgateway_api.src.error_handling import endpoint_error_handling
from operationsgateway_api.src.records.image_series import ImageSeries
from operationsgateway_api.src.records.record import Record

router = APIRouter()
AuthoriseToken = Annotated[str, Depends(authorise_token)]


@router.get(
    "/image-series/{record_id}/{channel_name}/frames/{frame_index}",
    summary="Get one full-size frame from an image series",
    response_description="Frame in .png format",
    tags=["Images"],
    response_class=Response,
    responses={200: {"content": {"image/png": {}}}},
)
@endpoint_error_handling
async def get_image_series_frame(
    record_id: str,
    channel_name: str,
    frame_index: NonNegativeInt,
    access_token: AuthoriseToken,
    colourmap_name: Optional[str] = Query(
        None,
        description="The name of the matplotlib colour map to apply",
    ),
    upper_level: int = Query(
        255,
        description="The upper level threshold for false colour (0-255)",
        ge=0,
        le=65535,
    ),
    lower_level: int = Query(
        0,
        description="The lower level threshold for false colour (0-255)",
        ge=0,
        le=65535,
    ),
    limit_bit_depth: int = Query(
        8,
        description=(
            "The bit depth to which `lower_level` and `upper_level` are relative. This "
            "can be any value as long as it is consistent with the provided levels, "
            "but is intended to reflect the original bit depth of the raw data, so "
            "meaningful values can be displayed and set in the frontend."
        ),
        ge=0,
        le=16,
    ),
    original_image: bool = Query(
        False,
        description="Return the original frame in PNG format without any"
        " false colour applied (false)",
    ),
) -> Response:
    """
    This endpoint can be used to retrieve one full-size frame of an image series by
    specifying the record ID, channel name and the (zero based) index of the frame.
    Frames are returned as a .png file, by default with false colour applied or
    optionally as the original frame by setting 'original_image' to True.

    The false colour parameters work in the same way as for a normal image.
    """
    if colourmap_name is None:
        colourmap_name = await ImageSeries.get_preferred_colourmap(access_token)

    image_bytes = await ImageSeries.get_image(
        record_id=record_id,
        channel_name=channel_name,
        frame_index=frame_index,
        original_image=original_image,
        lower_level=lower_level,
        upper_level=upper_level,
        limit_bit_depth=limit_bit_depth,
        colourmap_name=colourmap_name,
    )
    return Response(image_bytes, media_type="image/png")


@router.get(
    "/image-series/{record_id}/{channel_name}/frames/{frame_index}/crosshair",
    summary=(
        "Get row (varying x, fixed y co-ordinates) and column (fixed x, "
        "varying y co-ordinates) intensities for a frame of an image series at a "
        "given position, or by default for the centroid"
    ),
    response_description=(
        "Row (varying x, fixed y co-ordinates) and column (fixed x, varying y "
        "co-ordinates) intensities/FWHM"
    ),
    tags=["Images"],
)
@endpoint_error_handling
async def get_image_series_frame_crosshair_intensity(
    record_id: str,
    channel_name: str,
    frame_index: NonNegativeInt,
    access_token: AuthoriseToken,
    position: Optional[Json] = Query(
        None,
        description="(x, y) co-ordinates to return the intensity for",
    ),
):
    """
    This endpoint can be used to obtain the row (varying x, fixed y
    co-ordinates) and column (fixed x, varying y co-ordinates) intensity and
    full width half maxima of one frame of an image series. If no position is
    provided, the centroid will be calculated for the frame and that position used.
    """
    orig_img_array = await get_frame_array(
        record_id=record_id,
        channel_name=channel_name,
        frame_index=frame_index,
    )

    position_x, position_y = ImageSeries.validate_position(position, orig_img_array)

    column = orig_img_array[:, position_x]
    row = orig_img_array[position_y, :]
    column_dict = ImageSeries.extract_image_intensity(position_x, column)
    row_dict = ImageSeries.extract_image_intensity(position_y, row)
    return {"row": row_dict, "column": column_dict}


async def get_frame_array(
    record_id: str,
    channel_name: str,
    frame_index: int,
) -> np.ndarray:
    """
    Get a np.ndarray for one frame of an image series, with the bits shifted back to
    the positions they had in the raw data (as is done for normal images) so that the
    intensities are the original pixel values.
    """
    raw_bit_depth = await Record.get_raw_bit_depth(
        record_id=record_id,
        channel_name=channel_name,
    )
    png_bytes = await ImageSeries.get_frame(
        record_id=record_id,
        channel_name=channel_name,
        frame_index=frame_index,
    )
    img_array = np.array(PILImage.open(BytesIO(png_bytes)))
    return Record._bit_shift_to_raw(img_array=img_array, raw_bit_depth=raw_bit_depth)
