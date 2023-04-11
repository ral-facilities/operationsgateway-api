from io import BytesIO
import logging
from typing import Tuple

import numpy as np
from PIL import Image as PILImage

from operationsgateway_api.src.config import Config
from operationsgateway_api.src.exceptions import ImageError, ImageNotFoundError
from operationsgateway_api.src.models import ImageModel
from operationsgateway_api.src.mongo.interface import MongoDBInterface
from operationsgateway_api.src.records.echo_interface import EchoInterface
from operationsgateway_api.src.records.false_colour_handler import FalseColourHandler
from operationsgateway_api.src.records.thumbnail_handler import ThumbnailHandler


log = logging.getLogger()


class Image:
    lookup_table_16_to_8_bit = [i / 256 for i in range(65536)]

    def __init__(self, image: ImageModel) -> None:
        self.image = image

    def store(self) -> None:
        """
        Save the image on Echo an instance of S3 object storage
        """

        image_bytes = BytesIO()
        try:
            image = PILImage.fromarray(self.image.data)
            image.save(image_bytes, format="PNG")
        except TypeError as exc:
            log.exception(msg=exc)
            raise ImageError("Image data is not in correct format to be read") from exc

        echo = EchoInterface()
        echo.upload_file_object(image_bytes, self.image.path)

    def create_thumbnail(self) -> None:
        """
        Using the object's image data, create a thumbnail of the image and store it as
        an attribute of this object
        """
        # TODO - look at ingestion time and see if this slows things down

        echo = EchoInterface()
        image_bytes = echo.download_file_object(self.image.path)

        img = PILImage.open(image_bytes)
        img.thumbnail(Config.config.images.image_thumbnail_size)
        # convert 16 bit greyscale thumbnails to 8 bit to save space
        if img.mode == "I":
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
    async def get_image(
        record_id: str,
        channel_name: str,
        original_image: bool,
        lower_level: int,
        upper_level: int,
        colourmap_name: str,
    ) -> BytesIO:
        """
        Retrieve an image from disk and return the bytes of the image in a BytesIO
        object depending on what the user has requested.

        If 'original_image' is set to True then just return the unprocessed bytes of the
        image read from disk, otherwise apply false colour to the image either using the
        parameters provided or using defaults where they are not provided.

        If an image cannot be found, some error checking is done by looking to see if
        the record ID exists in the first place. Depending on what is found in the
        database, an appropriate exception (and error message) is raised
        """
        try:
            original_image_path = Image.get_image_path(
                record_id,
                channel_name,
                full_path=False,
            )

            echo = EchoInterface()
            image_bytes = echo.download_file_object(original_image_path)

            if original_image:
                return image_bytes
            else:
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
        except (OSError, RuntimeError) as exc:
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
    def get_image_path(
        record_id: str,
        channel_name: str,
        full_path: bool = True,
    ) -> str:
        """
        Returns an image path given a record ID and channel name. By default, a full
        path is returned, although this can be changed to not return the base directory
        by using the `full_path` argument.
        """

        # TODO - `full_path` not needed, should just be a single liner now
        if full_path:
            return (
                f"{Config.config.mongodb.image_store_directory}/{record_id}/"
                f"{channel_name}.png"
            )
        else:
            return f"{record_id}/{channel_name}.png"
