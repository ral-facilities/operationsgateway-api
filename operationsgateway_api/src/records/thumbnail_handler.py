import base64
from io import BytesIO

from PIL import Image


class ThumbnailHandler:
    @staticmethod
    def convert_to_base64(image: Image.Image) -> bytes:
        with BytesIO() as buf:
            image.save(buf, format="PNG")
            return base64.b64encode(buf.getvalue())

    @staticmethod
    def truncate_base64(base64_thumbnail):
        return base64_thumbnail[:50]
