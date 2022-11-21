import base64
import logging
import os

from fastapi.responses import FileResponse
from PIL import Image as PILImage

from operationsgateway_api.src.config import Config
from operationsgateway_api.src.exceptions import ImageError, ImageNotFoundError
from operationsgateway_api.src.models import ImageModel
from operationsgateway_api.src.mongo.interface import MongoDBInterface
from operationsgateway_api.src.records.thumbnail_handler import ThumbnailHandler


log = logging.getLogger()


class Image:
    def __init__(self, image: ImageModel):
        self.image = image

    def store(self):
        record_id, _ = self.extract_metadata_from_path()

        try:
            os.makedirs(
                f"{Config.config.mongodb.image_store_directory}/{record_id}",
                exist_ok=True,
            )
            image_buffer = PILImage.fromarray(self.image.data)
            image_buffer.save(
                f"{Config.config.mongodb.image_store_directory}/{self.image.path}",
            )
        except OSError as exc:
            raise ImageError("Image folder structure has failed") from exc
        except TypeError as exc:
            raise ImageError("Image data is not in correct format to be read") from exc

    def create_thumbnail(self):
        img = PILImage.open(
            f"{Config.config.mongodb.image_store_directory}/{self.image.path}",
        )
        img.thumbnail(Config.config.app.image_thumbnail_size)
        self.thumbnail = ThumbnailHandler.convert_to_base64(img)

    def extract_metadata_from_path(self):
        record_id = self.image.path.split("/")[-2]
        channel_name = self.image.path.split("/")[-1].split(".")[0]

        return record_id, channel_name

    @staticmethod
    async def get_image(record_id, channel_name, string_response):
        try:
            if string_response:
                with open(Image.get_image_path(record_id, channel_name), "rb") as file:
                    return base64.b64encode(file.read())
            else:
                # TODO - get exception handling to work on this one
                return FileResponse(Image.get_image_path(record_id, channel_name))
        except (OSError, RuntimeError) as exc:
            # TODO - change to Record.count_records() and fix the circular import
            record_count = await MongoDBInterface.count_documents(
                "records",
                {
                    "_id": record_id,
                    f"channels.{channel_name}": {"$exists": True},
                },
            )

            if record_count == 1:
                log.error(
                    "Image could not be found on disk. Record ID: %s, channel name: %s",
                    record_id,
                    channel_name,
                )
                raise ImageError("Image could not be found on disk") from exc
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
                    " image should be available on disk",
                    record_count,
                )
                raise ImageError("Unexpected error finding image on disk") from exc

    @staticmethod
    def get_image_path(record_id, channel_name, full_path=True):
        """
        Returns an image path given a record ID and channel name. By default, a full
        path is returned, although this can be changed to not return the base directory
        by using the `full_path` argument.
        """

        if full_path:
            return (
                f"{Config.config.mongodb.image_store_directory}/{record_id}/"
                f"{channel_name}.png"
            )
        else:
            return f"{record_id}/{channel_name}.png"
