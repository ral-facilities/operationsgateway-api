from datetime import datetime
import json
from tempfile import SpooledTemporaryFile

from pydantic import ValidationError
import pymongo

from operationsgateway_api.src.channels.manifest_validator import ManifestValidator
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
            manifest_file: dict = json.load(manifest_input)
        except json.JSONDecodeError as exc:
            raise ChannelManifestError(
                f"Channel manifest file not valid JSON. {str(exc)}",
            ) from exc

        manifest_file["_id"] = self._add_id()

        self.data = self._use_model(manifest_file)

    async def insert(self) -> None:
        """
        Insert the channel manifest data into MongoDB
        """
        await MongoDBInterface.insert_one(
            "channels",
            self.data.dict(by_alias=True, exclude_unset=True),
        )

    async def validate(self, bypass_channel_check: bool) -> None:
        """
        Validate the user's incoming manifest file by comparing that with the latest
        version stored in the database
        """
        stored_manifest = await ChannelManifest.get_most_recent_manifest()

        # Validation can only be done if there's an existing manifest file stored
        if stored_manifest:
            validator = ManifestValidator(
                self.data,
                self._use_model(stored_manifest),
                bypass_channel_check,
            )
            validator.perform_validation()

    def _add_id(self) -> str:
        """
        Get current datetime and convert into a string, following standard format as
        used elsewhere in the code
        """

        return datetime.now().strftime(ID_DATETIME_FORMAT)

    def _use_model(self, data: dict) -> ChannelManifestModel:
        """
        Convert dict into Pydantic model, with exception handling wrapped around the
        code to perform this
        """
        try:
            return ChannelManifestModel(**data)
        except ValidationError as exc:
            raise ModelError(str(exc)) from exc

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
        return manifest.channels[channel_name]
