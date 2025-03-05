from PIL import Image
import pytest

from operationsgateway_api.src.exceptions import ImageError
from operationsgateway_api.src.records.false_colour_handler import FalseColourHandler


class TestFalseColour:
    def test_invalid_image_mode(self):
        image_path = "test/images/jet_image.png"
        pil_image = Image.open(image_path).convert("RGB")

        with pytest.raises(ImageError, match="Image mode RGB not recognised"):
            FalseColourHandler.get_pixel_depth(pil_image)
