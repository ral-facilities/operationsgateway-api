from __future__ import annotations

from abc import abstractmethod
from io import BytesIO
import logging

from operationsgateway_api.src.models import ImageModel
from operationsgateway_api.src.records.channel_object_abc import ChannelObjectABC


log = logging.getLogger()


class ImageABC(ChannelObjectABC):
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
    def upload_image(input_image: ImageABC) -> str | None: ...

    @staticmethod
    @abstractmethod
    async def get_image(
        record_id: str,
        channel_name: str,
        colourmap_name: str,
    ) -> BytesIO: ...

    @staticmethod
    @abstractmethod
    async def get_preferred_colourmap(access_token: str) -> str: ...
