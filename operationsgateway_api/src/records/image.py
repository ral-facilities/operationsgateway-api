from __future__ import annotations

from io import BytesIO
import logging
from typing import Tuple

from botocore.exceptions import ClientError
import numpy as np
from PIL import Image as PILImage

from operationsgateway_api.src.auth.jwt_handler import JwtHandler
from operationsgateway_api.src.config import Config
from operationsgateway_api.src.exceptions import (
    EchoS3Error,
    ImageError,
    ImageNotFoundError,
)
from operationsgateway_api.src.models import ImageModel
from operationsgateway_api.src.mongo.interface import MongoDBInterface
from operationsgateway_api.src.records.echo_interface import EchoInterface
from operationsgateway_api.src.records.false_colour_handler import FalseColourHandler
from operationsgateway_api.src.records.thumbnail_handler import ThumbnailHandler


log = logging.getLogger()


class Image:
    lookup_table_16_to_8_bit = [i / 256 for i in range(65536)]
    echo_prefix = "images"

    def __init__(self, image: ImageModel) -> None:
        self.image = image

    def create_thumbnail(self) -> None:
        """
        Using the object's image data, create a thumbnail of the image and store it as
        an attribute of this object
        """

        log.info("Creating image thumbnail for %s", self.image.path)

        # Opening image then saving in a bytes object before using that to open and
        # generate a thumbnail as you can't produce a thumbnail when opening the image
        # using `fromarray()`
        image_bytes = BytesIO()
        img_temp = PILImage.fromarray(self.image.data)
        img_temp.save(image_bytes, format="PNG")

        img = PILImage.open(image_bytes)
        img.thumbnail(Config.config.images.image_thumbnail_size)
        # convert 16 bit greyscale thumbnails to 8 bit to save space
        if img.mode == "I":
            log.debug("Converting 16 bit greyscale thumbnail to 8 bit")
            img = img.point(Image.lookup_table_16_to_8_bit, "L")
        self.thumbnail = ThumbnailHandler.convert_to_base64(img)

    def extract_metadata_from_path(self) -> Tuple[str, str]:
        """
        Small string handler function to extract the record ID and channel name from the
        image's path
        """

        record_id = self.image.path.split("/")[-2]
        channel_name = self.image.path.split("/")[-1].split(".")[0]

        return record_id, channel_name

    @staticmethod
    def upload_image(input_image: Image) -> None:
        """
        Save the image on Echo S3 object storage
        """

        log.info("Storing image in a Bytes object: %s", input_image.image.path)
        image_bytes = BytesIO()
        try:
            image = PILImage.fromarray(input_image.image.data)
            image.save(image_bytes, format="PNG")
        except TypeError as exc:
            log.exception(msg=exc)
            raise ImageError("Image data is not in correct format to be read") from exc

        echo = EchoInterface()
        storage_path = Image.get_full_path(input_image.image.path)
        log.info("Storing image on S3: %s", storage_path)
        echo.upload_file_object(image_bytes, storage_path)

    @staticmethod
    async def get_image(
        record_id: str,
        channel_name: str,
        original_image: bool,
        lower_level: int,
        upper_level: int,
        colourmap_name: str,
    ) -> BytesIO:
        """
        Retrieve an image from Echo S3 and return the bytes of the image in a BytesIO
        object depending on what the user has requested.

        If 'original_image' is set to True then just return the unprocessed bytes of the
        image read from Echo S3, otherwise apply false colour to the image either using
        the parameters provided or using defaults where they are not provided.

        If an image cannot be found, some error checking is done by looking to see if
        the record ID exists in the first place. Depending on what is found in the
        database, an appropriate exception (and error message) is raised
        """

        log.info("Retrieving image and returning BytesIO object")
        echo = EchoInterface()

        try:
            original_image_path = Image.get_relative_path(record_id, channel_name)
            image_bytes = echo.download_file_object(
                Image.get_full_path(original_image_path),
            )

            if original_image:
                log.debug(
                    "Original image requested, return unmodified image bytes: %s",
                    original_image_path,
                )
                return image_bytes
            else:
                log.debug(
                    "False colour requested, applying false colour to image: %s",
                    original_image_path,
                )
                img_src = PILImage.open(image_bytes)
                orig_img_array = np.array(img_src)

                false_colour_image = FalseColourHandler.apply_false_colour(
                    orig_img_array,
                    FalseColourHandler.get_pixel_depth(img_src),
                    lower_level,
                    upper_level,
                    colourmap_name,
                )
                return false_colour_image
        except (ClientError, EchoS3Error) as exc:
            # Record.count_records() could not be used because that would cause a
            # circular import
            record_count = await MongoDBInterface.count_documents(
                "records",
                {
                    "_id": record_id,
                    f"channels.{channel_name}": {"$exists": True},
                },
            )

            if record_count == 1:
                log.error(
                    "Image could not be found on object storage. Record ID: %s, channel"
                    " name: %s",
                    record_id,
                    channel_name,
                )
                raise ImageError("Image could not be found on object storage") from exc
            elif record_count == 0:
                log.error(
                    "Image not available due to invalid record ID (%s) or channel name"
                    " (%s)",
                    record_id,
                    channel_name,
                )
                raise ImageNotFoundError(
                    "Image not available due to incorrect record ID or channel name",
                ) from exc
            else:
                log.error(
                    "Unexpected number of records (%d) found when verifying whether the"
                    " image should be available on object storage",
                    record_count,
                )
                raise ImageError(
                    "Unexpected error finding image on object storage",
                ) from exc

    @staticmethod
    def get_relative_path(record_id: str, channel_name: str) -> str:
        """
        Returns an image path given a record ID and channel name
        """

        return f"{record_id}/{channel_name}.png"

    @staticmethod
    def get_full_path(relative_path: str) -> str:
        return f"{Image.echo_prefix}/{relative_path}"

    @staticmethod
    async def get_preferred_colourmap(access_token: str) -> str:
        """
        Check the user's database record to see if they have a preferred colour map set
        """
        username = JwtHandler.get_payload(access_token)["username"]
        colourmap_name = await FalseColourHandler.get_preferred_colourmap(username)
        log.debug("Preferred colour map for %s is %s", username, colourmap_name)
        return colourmap_name
