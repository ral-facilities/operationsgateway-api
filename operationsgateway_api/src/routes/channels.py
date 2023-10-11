import logging

from fastapi import APIRouter, Depends, Path
import pymongo

from operationsgateway_api.src.auth.authorisation import authorise_token
from operationsgateway_api.src.channels.channel_manifest import ChannelManifest
from operationsgateway_api.src.error_handling import endpoint_error_handling
from operationsgateway_api.src.models import ChannelSummaryModel
from operationsgateway_api.src.records.record import Record

log = logging.getLogger()
router = APIRouter()


@router.get(
    "/channels/summary/{channel_name}",
    summary="Provide a summary of a given channel",
    response_description="Channel summary",
    tags=["Channels"],
)
@endpoint_error_handling
async def get_channel_summary(
    channel_name: str,# = Path(
        #"",
        #description="Channel name to provide a summary for",
    #),
    access_token: str = Depends(authorise_token),
):
    """
    Provide the dates of first and most recent pieces of data and the three most recent
    values of a channel
    """

    log.info("Getting channel summary for: %s", channel_name)

    first_date = await Record.get_date_of_channel_data(
        channel_name,
        [("_id", pymongo.ASCENDING)],
    )
    most_recent_date = await Record.get_date_of_channel_data(
        channel_name,
        [("_id", pymongo.DESCENDING)],
    )

    recent_data = await Record.get_recent_channel_values(channel_name)

    return ChannelSummaryModel(
        first_date=first_date,
        most_recent_date=most_recent_date,
        recent_sample=recent_data,
    )


@router.get(
    "/channels",
    summary="Get channels from the database",
    response_description="List of channels",
    tags=["Channels"],
)
@endpoint_error_handling
async def get_channels(
    access_token: str = Depends(authorise_token),
):
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
    channel_system_name: str,# = Path(
        #"",
        #description="Channel system name to lookup in manifest file",
    #),
    access_token: str = Depends(authorise_token),
):
    """
    Given a channel system name, provide the metadata for a single channel in the most
    recent manifest data
    """

    log.info("Get specific channel by its system name: %s", channel_system_name)

    channel = await ChannelManifest.get_channel(channel_system_name)

    return channel.dict(by_alias=True, exclude_unset=True)
