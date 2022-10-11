import base64
import os

from PIL import Image as PILImage

from operationsgateway_api.src.config import Config
from operationsgateway_api.src.models import Image as ImageModel
from operationsgateway_api.src.records.thumbnail_handler import ThumbnailHandler


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
        except OSError as e:
            # TODO - add proper exception
            print(f"IMAGE DIRECTORY CREATION OR IMAGE SAVE BROKE: {e}")
        except TypeError as e:
            # TODO - add proper exception
            print(f"IMAGE DATA NOT IN CORRECT FORMAT FOR PIL: {e}")

    # TODO - we don't store thumbnails in DB, oops
    def create_thumbnail(self):
        img = PILImage.open(
            f"{Config.config.mongodb.image_store_directory}/{self.image.path}",
        )
        self.thumbnail = ThumbnailHandler.convert_to_base64(img)

    def extract_metadata_from_path(self):
        record_id = self.image.path.split("/")[-2]
        channel_name = self.image.path.split("/")[-1].split(".")[0]

        return record_id, channel_name

    @staticmethod
    def get_image(record_id, channel_name):
        try:
            with open(Image.get_image_path(record_id, channel_name), "rb") as file:
                return base64.b64encode(file.read())
        except OSError as e:
            # TODO - add proper exception
            print(f"FILE COULD NOT BE OPENED: {e}")

    @staticmethod
    def get_image_path(record_id, channel_name, full_path=True):
        # TODO - turn below into a docstring or comment or something
        # /root/seg_dev/og-images/20220408002834/N_COMP_FF_IMAGE.png
        # 20220408002834/N_COMP_FF_IMAGE.png
        if full_path:
            return (
                f"{Config.config.mongodb.image_store_directory}/{record_id}/"
                f"{channel_name}.png"
            )
        else:
            return f"{record_id}/{channel_name}.png"
