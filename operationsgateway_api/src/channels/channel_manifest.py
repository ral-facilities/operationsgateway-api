from datetime import datetime
import json
from tempfile import SpooledTemporaryFile

from pydantic import ValidationError
import pymongo

from operationsgateway_api.src.constants import ID_DATETIME_FORMAT
from operationsgateway_api.src.exceptions import ChannelManifestError, ModelError
from operationsgateway_api.src.models import ChannelManifestModel, ChannelModel
from operationsgateway_api.src.mongo.interface import MongoDBInterface


class ChannelManifest:
    def __init__(self, manifest_input: SpooledTemporaryFile) -> None:
        """
        Load JSON from a temporary file and put it into a Pydantic model
        """
        try:
            manifest_file = json.load(manifest_input)
        except json.JSONDecodeError as exc:
            raise ChannelManifestError(
                f"Channel manifest file not valid JSON. {str(exc)}",
            )

        manifest_file["_id"] = self._add_id()

        try:
            self.data = ChannelManifestModel(**manifest_file)
        except ValidationError as exc:
            raise ModelError(str(exc)) from exc

    async def insert(self) -> None:
        """
        Insert the channel manifest data into MongoDB
        """
        await MongoDBInterface.insert_one(
            "channels",
            self.data.dict(by_alias=True, exclude_unset=True),
        )

    def _add_id(self) -> str:
        """
        Get current datetime and convert into a string, following standard format as
        used elsewhere in the code
        """

        return datetime.now().strftime(ID_DATETIME_FORMAT)

    @staticmethod
    async def get_most_recent_manifest() -> dict:
        """
        Get the most up to date manifest file from MongoDB and return it to the user
        """
        manifest_data = await MongoDBInterface.find_one(
            "channels",
            sort=[("_id", pymongo.DESCENDING)],
        )

        return manifest_data

    @staticmethod
    async def get_channel(channel_name: str) -> ChannelModel:
        """
        Look for the most recent manifest file and return a specific channel's metadata
        from that file
        """
        manifest_data = await ChannelManifest.get_most_recent_manifest()
        manifest = ChannelManifestModel(**manifest_data)
        try:
            return manifest.channels[channel_name]
        except KeyError as exc:
            raise ChannelManifestError(
                f"Channel '{channel_name}' cannot be found"
            ) from exc
