from __future__ import annotations

from io import BytesIO
import logging

import numpy as np
from PIL import Image

from operationsgateway_api.src.auth.jwt_handler import JwtHandler
from operationsgateway_api.src.config import Config
from operationsgateway_api.src.exceptions import EchoS3Error
from operationsgateway_api.src.models import FloatImageModel
from operationsgateway_api.src.records.echo_interface import EchoInterface
from operationsgateway_api.src.records.false_colour_handler import FalseColourHandler
from operationsgateway_api.src.records.image_abc import ImageABC
from operationsgateway_api.src.records.thumbnail_handler import ThumbnailHandler


log = logging.getLogger()


class FloatImage(ImageABC):
    echo_prefix = "float_images"
    echo_extension = "npz"

    def __init__(self, image: FloatImageModel) -> None:
        super().__init__(image)

    @staticmethod
    def get_absolute_max(array: np.ndarray) -> float:
        """Returns the largest absolute value in the array, ignoring nans. If all values
        are nan or 0, then 1 is returned. This lets us safely divide by this number when
        normalising the image.
        """
        if np.all(np.isnan(array)) or np.all(array == 0):
            return 1
        else:
            return np.nanmax(np.absolute(array))

    def create_thumbnail(self) -> None:
        """
        Using the object's image data, create a thumbnail of the image and store it as
        an attribute of this object as base64. The thumbnail uses the LA mode, with the
        L channel representing normalised values from the original array and the alpha
        being 0 for nans and 255 for all other values.
        """
        log.info("Creating image thumbnail for %s", self.image.path)
        absolute_max = FloatImage.get_absolute_max(self.image.data)
        normalised_data = 255 * (self.image.data / (2 * absolute_max) + 0.5)
        alpha = np.where(np.isnan(self.image.data), np.uint8(0), np.uint8(255))
        la_data = np.stack(arrays=[normalised_data.astype(np.uint8), alpha], axis=-1)
        la_image = Image.fromarray(la_data, "LA")
        la_image.thumbnail(Config.config.float_images.thumbnail_size)
        self.thumbnail = ThumbnailHandler.convert_to_base64(la_image)
        la_image.close()

    @staticmethod
    def upload_image(input_image: FloatImage) -> str | None:
        """
        Save the image on Echo S3 object storage as a compressed numpy array (.npz)
        """

        log.info("Storing float image in a Bytes object: %s", input_image.image.path)
        image_bytes = BytesIO()
        np.savez_compressed(image_bytes, input_image.image.data)
        echo = EchoInterface()
        storage_path = FloatImage.get_full_path(input_image.image.path)
        log.info("Storing float image on S3: %s", storage_path)

        try:
            echo.upload_file_object(image_bytes, storage_path)
            return None  # No failure
        except EchoS3Error:
            # Extract the channel name and propagate it
            channel_name = input_image.get_channel_name_from_path()
            log.error("Failed to upload float image for channel: %s", channel_name)
            return channel_name

    @staticmethod
    async def get_image(
        record_id: str,
        channel_name: str,
        colourmap_name: str,
    ) -> BytesIO:
        """
        Get the original numpy array, then apply the specified colourmap to the values.
        The returned BytesIO encode the image as a png. For use when displaying data.
        """
        log.info("Retrieving float image and returning BytesIO object")
        array_bytes = await FloatImage.get_bytes(record_id, channel_name)
        array_bytes.seek(0)
        npz_file = np.load(array_bytes)
        array = npz_file["arr_0"]
        npz_file.close()
        absolute_max = FloatImage.get_absolute_max(array)
        return FalseColourHandler.apply_false_colour_float(
            array,
            absolute_max,
            colourmap_name,
        )

    @staticmethod
    async def get_preferred_colourmap(access_token: str) -> str:
        """
        Check the user's database record to see if they have a preferred colour map set
        """
        username = JwtHandler.get_payload(access_token)["username"]
        colourmap_name = await FalseColourHandler.get_preferred_float_colourmap(
            username,
        )
        log.debug("Preferred colour map for %s is %s", username, colourmap_name)
        return colourmap_name
