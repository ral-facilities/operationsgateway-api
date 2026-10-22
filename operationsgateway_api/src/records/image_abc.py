from __future__ import annotations

from abc import abstractmethod
from io import BytesIO
import logging
from typing import Any

from operationsgateway_api.src.models import ImageModel
from operationsgateway_api.src.records.channel_object_abc import ChannelObjectABC

log = logging.getLogger()


class ImageABC(ChannelObjectABC):
    def __init__(self, image: ImageModel) -> None:
        self.image = image
        self.thumbnail: bytes | None = None

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
    async def get_image(*args: Any, **kwargs: Any) -> bytes | BytesIO:
        """
        Retrieve the stored image. The parameters differ between image types, for
        example a series also needs the index of the frame to retrieve, so each type
        declares its own.
        """

    @staticmethod
    @abstractmethod
    async def get_preferred_colourmap(access_token: str) -> str: ...
