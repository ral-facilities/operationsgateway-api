import logging
from typing import Optional

from fastapi import APIRouter, Depends, Path, Query, Response
from typing_extensions import Annotated

from operationsgateway_api.src.auth.authorisation import authorise_token
from operationsgateway_api.src.error_handling import endpoint_error_handling
from operationsgateway_api.src.records.float_image import FloatImage

log = logging.getLogger()
router = APIRouter()
AuthoriseToken = Annotated[str, Depends(authorise_token)]


@router.get(
    "/images/float/{record_id}/{channel_name}",
    summary="Get float image",
    response_description="Image in .png format with false colour applied",
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
):
    if colourmap_name is None:
        colourmap_name = await FloatImage.get_preferred_colourmap(access_token)

    bytes_io = await FloatImage.get_image(record_id, channel_name, colourmap_name)
    return Response(bytes_io.getvalue(), media_type="image/png")
