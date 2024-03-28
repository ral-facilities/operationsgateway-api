from PIL import Image
import pytest

from operationsgateway_api.src.exceptions import ImageError
from operationsgateway_api.src.records.false_colour_handler import FalseColourHandler


class TestFalseColour:
    def test_invalid_bits_per_pixel(self):

        with pytest.raises(ImageError, match="7 bits per pixel is not supported"):
            FalseColourHandler.apply_false_colour(
                image_array="",
                bits_per_pixel="7",
                lower_level=4,
                upper_level=8,
                colourmap_name="test",
            )

    def test_invalid_image_mode(self):
        image_path = "test/records/jet_image.png"
        pil_image = Image.open(image_path).convert("RGB")

        with pytest.raises(ImageError, match="Image mode RGB not recognised"):
            FalseColourHandler.get_pixel_depth(pil_image)
