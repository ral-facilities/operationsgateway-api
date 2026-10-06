from fastapi import APIRouter, Depends, Path, Response
from typing_extensions import Annotated

from operationsgateway_api.src.auth.authorisation import authorise_token
from operationsgateway_api.src.error_handling import endpoint_error_handling
from operationsgateway_api.src.records.image_series import ImageSeries

router = APIRouter()
AuthoriseToken = Annotated[str, Depends(authorise_token)]


@router.get(
    "/image-series/{record_id}/{channel_name}/frames/{frame_index}",
    summary="Get one full-size frame from an image series",
    tags=["Images"],
    response_class=Response,
    responses={200: {"content": {"image/png": {}}}},
)
@endpoint_error_handling
async def get_image_series_frame(
    record_id: str,
    channel_name: str,
    frame_index: Annotated[int, Path(ge=0)],
    access_token: AuthoriseToken,
) -> Response:
    """Retrieve one image-series frame as a PNG."""
    png_bytes = await ImageSeries.get_frame(
        record_id=record_id,
        channel_name=channel_name,
        frame_index=frame_index,
    )

    return Response(content=png_bytes, media_type="image/png")