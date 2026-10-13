from __future__ import annotations

from io import BytesIO
import logging
from typing import Optional

from PIL import Image as PILImage, PngImagePlugin

from operationsgateway_api.src.exceptions import (
    EchoS3Error,
    ImageError,
)
from operationsgateway_api.src.records.echo_interface import get_echo_interface
from operationsgateway_api.src.records.greyscale_image_abc import GreyscaleImageABC
from operationsgateway_api.src.records.image_abc import ImageABC

log = logging.getLogger()


class Image(GreyscaleImageABC):
    echo_prefix = "images"
    echo_extension = "png"

    def create_thumbnail(self) -> None:
        """
        Using the object's image data, create a thumbnail of the image and store it as
        an attribute of this object
        """
        self._create_greyscale_thumbnail(self.image.data)

    @staticmethod
    async def upload_image(input_image: ImageABC) -> Optional[str]:
        """
        Save the image on Echo S3 object storage
        """

        log.info("Storing image in a Bytes object: %s", input_image.image.path)
        image_bytes = BytesIO()
        try:
            image = PILImage.fromarray(input_image.image.data)
            bit_depth = input_image.image.bit_depth
            if bit_depth is not None and 0 < bit_depth <= 16:
                info = PngImagePlugin.PngInfo()
                sbit = bit_depth.to_bytes(1, byteorder="big")
                info.add(b"sBIT", sbit)
                image.save(image_bytes, format="PNG", pnginfo=info)
            else:
                image.save(image_bytes, format="PNG")
        except TypeError as exc:
            log.exception(msg=exc)
            raise ImageError("Image data is not in correct format to be read") from exc

        echo_interface = get_echo_interface()
        storage_path = Image.get_full_path(input_image.image.path)
        log.info("Storing image on S3: %s", storage_path)

        try:
            await echo_interface.upload_file_object(image_bytes, storage_path)
            return None  # No failure
        except EchoS3Error:
            # Extract the channel name and propagate it
            channel_name = input_image.get_channel_name_from_path()
            log.error("Failed to upload image for channel: %s", channel_name)
            return channel_name

    @staticmethod
    async def get_image(
        record_id: str,
        channel_name: str,
        original_image: bool,
        lower_level: int,
        upper_level: int,
        limit_bit_depth: int,
        colourmap_name: str,
    ) -> bytes:
        """
        Retrieve an image from Echo S3 and return the bytes of the image depending on
        what the user has requested.

        If 'original_image' is set to True then just return the unprocessed bytes of the
        image read from Echo S3, otherwise apply false colour to the image either using
        the parameters provided or using defaults where they are not provided.

        If an image cannot be found, some error checking is done by looking to see if
        the record ID exists in the first place. Depending on what is found in the
        database, an appropriate exception (and error message) is raised
        """

        msg = "Retrieving image and returning BytesIO object: %s %s"
        log.info(msg, record_id, channel_name)
        image_bytes = await Image.get_bytes(
            record_id=record_id,
            channel_name=channel_name,
        )
        return Image.apply_false_colour(
            image_bytes=image_bytes,
            original_image=original_image,
            lower_level=lower_level,
            upper_level=upper_level,
            limit_bit_depth=limit_bit_depth,
            colourmap_name=colourmap_name,
        )
