from __future__ import annotations

from abc import ABC, abstractmethod
from io import BytesIO
import logging

from operationsgateway_api.src.exceptions import ImageError, ImageNotFoundError
from operationsgateway_api.src.models import ImageModel
from operationsgateway_api.src.mongo.interface import MongoDBInterface
from operationsgateway_api.src.records.echo_interface import EchoInterface


log = logging.getLogger()


class ImageABC(ABC):
    def __init__(self, image: ImageModel) -> None:
        self.image = image

    @property
    @abstractmethod
    def echo_prefix(self) -> str: ...

    @property
    @abstractmethod
    def echo_extension(self) -> str: ...

    @abstractmethod
    def create_thumbnail(self) -> None: ...

    def get_channel_name_from_path(self) -> str:
        """
        Small string handler function to extract the channel name from the path
        """
        return self.image.path.split("/")[-1].split(".")[0]

    @staticmethod
    @abstractmethod
    async def upload_image(input_image: ImageABC) -> str | None: ...

    @staticmethod
    @abstractmethod
    async def get_image(
        record_id: str,
        channel_name: str,
        colourmap_name: str,
    ) -> BytesIO: ...

    @staticmethod
    async def _handle_get_image_exception(
        record_id: str,
        channel_name: str,
        exc: Exception,
    ) -> None:
        filter_ = {"_id": record_id, f"channels.{channel_name}": {"$exists": True}}
        record_count = await MongoDBInterface.count_documents("records", filter_)
        if record_count == 1:
            msg = (
                "Image could not be found on object storage. Record ID: %s, channel"
                " name: %s"
            )
            log.error(msg, record_id, channel_name)
            raise ImageError("Image could not be found on object storage") from exc
        elif record_count == 0:
            msg = (
                "Image not available due to invalid record ID (%s) or channel name (%s)"
            )
            log.error(msg, record_id, channel_name)
            msg = "Image not available due to incorrect record ID or channel name"
            raise ImageNotFoundError(msg) from exc
        else:
            msg = (
                "Unexpected number of records (%d) found when verifying whether the"
                " image should be available on object storage"
            )
            log.error(msg, record_count)
            msg = "Unexpected error finding image on object storage"
            raise ImageError(msg) from exc

    @classmethod
    def get_relative_path(
        cls,
        record_id: str,
        channel_name: str,
        use_subdirectories: bool = True,
    ) -> str:
        """
        Returns a relative image path given a record ID and channel name. The path is
        relative to the base directory of where images are stored in Echo
        """
        directories = EchoInterface.format_record_id(record_id, use_subdirectories)
        return f"{directories}/{channel_name}.{cls.echo_extension}"

    @classmethod
    def get_full_path(cls, relative_path: str) -> str:
        """
        Converts a relative image path to a full path by adding the 'prefix' onto a
        relative path of an image. The full path doesn't include the bucket name
        """
        return f"{cls.echo_prefix}/{relative_path}"

    @staticmethod
    @abstractmethod
    async def get_preferred_colourmap(access_token: str) -> str: ...
