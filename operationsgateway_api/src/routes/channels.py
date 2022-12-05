import logging

from fastapi import APIRouter, Path

from operationsgateway_api.src.channels.channel_manifest import ChannelManifest
from operationsgateway_api.src.error_handling import endpoint_error_handling

log = logging.getLogger()
router = APIRouter()


@router.get(
    "/channels",
    summary="Get channels from the database",
    response_description="List of channels",
    tags=["Channels"],
)
@endpoint_error_handling
async def get_channels():
    """
    Get all the channel metadata from the database and return to the user
    """

    log.info("Getting channel metadata from database")

    return await ChannelManifest.get_most_recent_manifest()


@router.get(
    "/channels/{channel_system_name}",
    summary="Get channel by system name",
    response_description="Channel",
    tags=["Channels"],
)
@endpoint_error_handling
async def get_channel_by_system_name(
    channel_system_name: str = Path(  # noqa: B008
        "",
        description="Channel system name to lookup in manifest file",
    ),
):
    """
    Given a channel system name, provide the metadata for a single channel in the most
    recent manifest data
    """

    log.info("Get specific channel by its system name: %s", channel_system_name)

    channel = await ChannelManifest.get_channel(channel_system_name)

    return channel.dict(exclude_unset=True)
