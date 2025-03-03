import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, Path, Query, Response
import numpy as np
from PIL import Image as PILImage
from pydantic import Json
from typing_extensions import Annotated

from operationsgateway_api.src.auth.authorisation import authorise_token
from operationsgateway_api.src.error_handling import endpoint_error_handling
from operationsgateway_api.src.models import PartialRecordModel
from operationsgateway_api.src.records.false_colour_handler import FalseColourHandler
from operationsgateway_api.src.records.image import Image
from operationsgateway_api.src.records.record import Record

log = logging.getLogger()
router = APIRouter()
AuthoriseToken = Annotated[str, Depends(authorise_token)]


@router.get(
    "/images/{record_id}/{channel_name}",
    summary="Get full-size image from disk",
    response_description="Image in .png format",
    tags=["Images"],
)
@endpoint_error_handling
async def get_full_image(
    record_id: Annotated[
        str,
        Path(
            ...,
            description="ID of the record (usually timestamp)",
        ),
    ],
    channel_name: Annotated[
        str,
        Path(
            ...,
            description="Channel name containing the image",
        ),
    ],
    access_token: AuthoriseToken,
    colourmap_name: Optional[str] = Query(
        None,
        description="The name of the matplotlib colour map to apply",
    ),
    upper_level: Optional[int] = Query(
        255,
        description="The upper level threshold for false colour (0-255)",
        ge=0,
        le=65535,
    ),
    lower_level: Optional[int] = Query(
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
    original_image: Optional[bool] = Query(
        False,
        description="Return the original image in PNG format without any"
        " false colour applied (false)",
    ),
    functions: List[Json] = Query(
        None,
        description="Functions to evaluate on the record data being returned",
    ),
):
    """
    This endpoint can be used to retrieve a full-size image by specifying the shot
    number and channel name. Images are stored on disk and can be returned as a .png
    file, by default with false colour applied or optionally as the original image by
    setting 'original_image' to True.

    If `channel_name` matches one of the entries in `functions`, then that will be
    evaluated to generate the returned image.
    """

    if colourmap_name is None:
        colourmap_name = await Image.get_preferred_colourmap(access_token)

    image_bytes = await get_image_bytes(
        record_id=record_id,
        channel_name=channel_name,
        colourmap_name=colourmap_name,
        upper_level=upper_level,
        lower_level=lower_level,
        limit_bit_depth=limit_bit_depth,
        original_image=original_image,
        functions=functions,
    )
    return Response(image_bytes, media_type="image/png")


@router.get(
    "/images/{record_id}/{channel_name}/crosshair",
    summary=(
        "Get row (varying x, fixed y co-ordinates) and column (fixed x, "
        "varying y co-ordinates) intensities for a given position, or by "
        "default for the centroid"
    ),
    response_description=(
        "Row (varying x, fixed y co-ordinates) and column (fixed x, varying y "
        "co-ordinates) intensities/FWHM"
    ),
    tags=["Images"],
)
@endpoint_error_handling
async def get_crosshair_intensity(
    record_id: Annotated[
        str,
        Path(
            ...,
            description="ID of the record (usually timestamp)",
        ),
    ],
    channel_name: Annotated[
        str,
        Path(
            ...,
            description="Channel name containing the image",
        ),
    ],
    access_token: AuthoriseToken,
    functions: List[Json] = Query(
        None,
        description="Functions to evaluate on the record data being returned",
    ),
    position: Optional[Json] = Query(
        None,
        description="(x, y) co-ordinates to return the intensity for",
    ),
):
    """
    This endpoint can be used to obtain the row (varying x, fixed y
    co-ordinates) and column (fixed x, varying y co-ordinates) intensity and
    full width half maxima of an image by specifying the shot number and channel
    name. If no position is provided, the centroid will be calculated for the
    image and that position used.

    If `channel_name` matches one of the entries in `functions`, then that will be
    evaluated to generate the returned image.
    """
    orig_img_array = await get_image_array(
        record_id=record_id,
        channel_name=channel_name,
        colourmap_name=None,
        upper_level=255,
        lower_level=0,
        limit_bit_depth=8,
        original_image=True,
        functions=functions,
    )

    position_x, position_y = Image.validate_position(position, orig_img_array)

    column = orig_img_array[:, position_x]
    row = orig_img_array[position_y, :]
    column_dict = Image.extract_image_intensity(position_x, column)
    row_dict = Image.extract_image_intensity(position_y, row)
    return {"row": row_dict, "column": column_dict}


@router.get(
    "/images/colour_bar",
    summary="Get a colourbar image",
    response_description="Image in .png format",
    tags=["Images"],
)
@endpoint_error_handling
async def get_colourbar_image(
    access_token: AuthoriseToken,
    colourmap_name: Optional[str] = Query(
        None,
        description="The name of the matplotlib colour map to apply",
    ),
    upper_level: Optional[int] = Query(
        255,
        description="The upper level threshold for false colour (0-255)",
        ge=0,
        le=65535,
    ),
    lower_level: Optional[int] = Query(
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
):
    """
    This endpoint can be used to retrieve a colourbar image showing the colour spectrum
    for the specified colour map with the upper and lower limits set. If either limit
    is not specified then the default of 0 for the lower level and/or 255 for the upper
    level will be used.
    """

    if colourmap_name is None:
        colourmap_name = await Image.get_preferred_colourmap(access_token)

    colourbar_image_bytes = FalseColourHandler.create_colourbar(
        lower_level=lower_level,
        upper_level=upper_level,
        limit_bit_depth=limit_bit_depth,
        colourmap_name=colourmap_name,
    )
    colourbar_image_bytes.seek(0)
    return Response(colourbar_image_bytes.read(), media_type="image/png")


@router.get(
    "/images/colourmap_names",
    summary="Get a list of the available colourmaps",
    response_description="A list of available colourmaps in alphabetical order and"
    " including the reverse (_r) versions of each map",
    tags=["Images"],
)
@endpoint_error_handling
async def get_colourmap_names(
    access_token: AuthoriseToken,
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


async def get_image_bytes(
    record_id: str,
    channel_name: str,
    colourmap_name: str,
    upper_level: int,
    lower_level: int,
    limit_bit_depth: int,
    original_image: bool,
    functions: "list[dict]",
) -> bytes:
    """Get the bytes for the requested image (possibly as the output from
    one of the defined `functions`).
    """
    if functions:
        for function_dict in functions:
            if function_dict["name"] == channel_name:
                channels = await Record.apply_functions(
                    record=PartialRecordModel(_id=record_id),
                    functions=functions,
                    original_image=original_image,
                    lower_level=lower_level,
                    upper_level=upper_level,
                    limit_bit_depth=limit_bit_depth,
                    colourmap_name=colourmap_name,
                    return_thumbnails=False,
                )
                return channels[channel_name].data

    bytes_io = await Image.get_image(
        record_id=record_id,
        channel_name=channel_name,
        original_image=original_image,
        lower_level=lower_level,
        upper_level=upper_level,
        limit_bit_depth=limit_bit_depth,
        colourmap_name=colourmap_name,
    )
    return bytes_io.getvalue()


async def get_image_array(
    record_id: str,
    channel_name: str,
    colourmap_name: str,
    upper_level: int,
    lower_level: int,
    limit_bit_depth: int,
    original_image: bool,
    functions: "list[dict]",
) -> np.ndarray:
    """
    Get a np.ndarray for the requested image (possibly as the output from one of the
    defined `functions`).
    """
    if functions:
        for function_dict in functions:
            if function_dict["name"] == channel_name:
                channels = await Record.apply_functions(
                    record=PartialRecordModel(_id=record_id),
                    functions=functions,
                    original_image=original_image,
                    lower_level=lower_level,
                    upper_level=upper_level,
                    limit_bit_depth=limit_bit_depth,
                    colourmap_name=colourmap_name,
                    return_thumbnails=False,
                )
                return channels[channel_name].variable_value

    bytes_io = await Image.get_image(
        record_id=record_id,
        channel_name=channel_name,
        original_image=original_image,
        lower_level=lower_level,
        upper_level=upper_level,
        limit_bit_depth=limit_bit_depth,
        colourmap_name=colourmap_name,
    )
    image = PILImage.open(bytes_io)
    return np.array(image)
