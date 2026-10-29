import logging

from fastapi import APIRouter, Depends
from typing_extensions import Annotated

from operationsgateway_api.src.auth.authorisation import authorise_token
from operationsgateway_api.src.error_handling import endpoint_error_handling
from operationsgateway_api.src.models import TagModel
from operationsgateway_api.src.tags.tag import Tag

log = logging.getLogger()
router = APIRouter()


@router.get(
    "/tags",
    summary="Get the tags that can be applied to records",
    response_description="List of tags, with a description and whether each is active",
    tags=["Tags"],
    response_model=list[TagModel],
)
@endpoint_error_handling
async def get_tags(
    access_token: Annotated[str, Depends(authorise_token)],  # noqa: B008
):
    """
    Get the tags that can be applied to records.
    """

    log.info("Getting tags")
    return await Tag.get_all_tags_from_database()
