from __future__ import annotations

from abc import abstractmethod
from io import BytesIO
import logging
from typing import Any

import numpy as np
from PIL import Image as PILImage

from operationsgateway_api.src.config import Config
from operationsgateway_api.src.models import ImageModel
from operationsgateway_api.src.records.channel_object_abc import ChannelObjectABC
from operationsgateway_api.src.records.thumbnail_handler import ThumbnailHandler

log = logging.getLogger()


class ImageABC(ChannelObjectABC):
    lookup_table_16_to_8_bit = [i / 256 for i in range(65536)]

    def __init__(self, image: ImageModel) -> None:
        self.image = image
        self.thumbnail: bytes | None = None

    def _normalise_bit_depth(self) -> None:
        """
        Prepare `self.image.data` for storage at either 8 or 16 bits.

        Data is only ever stored as 8 or 16 bit, so data with any other bit depth is
        shifted into the most significant bits. So a full scale 12 bit pixel is
        also full scale once stored, rather than looking dim in a 16 bit container.
        ImageModel.bit_depth` keeps the originally specified depth.
        """
        if isinstance(self.image.bit_depth, int):
            bit_depth = self.image.bit_depth
            if bit_depth <= 8 and self.image.data.dtype != np.uint8:
                msg = (
                    "Specified bit depth is lower than actual bit depth with dtype "
                    "of %s, only data in the %s least significant bits will be kept"
                )
                log.warning(msg, self.image.data.dtype, bit_depth)
            elif bit_depth > 16:
                log.warning(
                    "Specified bit depth is higher than the max supported depth of 16, "
                    "only data in the 16 most significant bits will be kept",
                )
        else:
            if self.image.data.dtype == np.uint8:
                bit_depth = 8
            else:
                # In principle this could be data with any number of bits, but we have
                # no way of knowing without an explicit bit_depth so default to 16
                bit_depth = 16

        # We only store data as either 8 or 16 bit PNGs, scale to most significant bits
        if bit_depth <= 8:
            target_bit_depth = 8
            target_dtype = np.uint8
        else:
            target_bit_depth = 16
            target_dtype = np.uint16

        self.image.data = self.image.data.astype(target_dtype)
        shifted_data = self.image.data * 2 ** (target_bit_depth - bit_depth)
        # Negative shifts may result in a float output, so cast the type again
        self.image.data = shifted_data.astype(target_dtype)

    def _create_greyscale_thumbnail(self, data: np.ndarray) -> None:
        """
        Create a thumbnail from `data`, a 2D 8 or 16 bit greyscale array, and store
        it as an attribute of this object.

        Shared by the image types that store greyscale data, which differ only in
        which array they take the thumbnail from.
        """

        log.info("Creating image thumbnail for %s", self.image.path)

        # Opening image then saving in a bytes object before using that to open and
        # generate a thumbnail as you can't produce a thumbnail when opening the image
        # using `fromarray()`
        image_bytes = BytesIO()
        img_temp = PILImage.fromarray(data)
        img_temp.save(image_bytes, format="PNG")

        img = PILImage.open(image_bytes)
        # Images of a certain mode must be converted to mode I to avoid a ValueError
        # where PIL complains the image is in the wrong mode
        if img.mode == "I;16":
            img = img.convert("I")

        img.thumbnail(Config.config.images.thumbnail_size)
        # convert 16 bit greyscale thumbnails to 8 bit to save space
        if img.mode == "I":
            log.debug("Converting 16 bit greyscale thumbnail to 8 bit")
            img = img.point(ImageABC.lookup_table_16_to_8_bit, "L")
        self.thumbnail = ThumbnailHandler.convert_to_base64(img)

        img.close()

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
