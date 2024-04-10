import base64
from io import BytesIO
import logging

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image as PILImage

from operationsgateway_api.src.config import Config
from operationsgateway_api.src.exceptions import (
    ImageError,
    MissingAttributeError,
    QueryParameterError,
)
from operationsgateway_api.src.records.colourmap_mapping import ColourmapMapping
from operationsgateway_api.src.users.preferences import UserPreferences


log = logging.getLogger()


class FalseColourHandler:
    default_colour_map_name = Config.config.images.default_colour_map
    colourbar_height_pixels = Config.config.images.colourbar_height_pixels
    preferred_colour_map_pref_name = Config.config.images.preferred_colour_map_pref_name
    colourmap_names = ColourmapMapping.get_colourmap_mappings()

    @staticmethod
    async def get_preferred_colourmap(
        username: str,
    ) -> str:
        """
        Check whether the user has stored a preference for which colour map they prefer
        to use. Return the value if they have, otherwise return None.
        """
        try:
            return await UserPreferences.get(
                username,
                FalseColourHandler.preferred_colour_map_pref_name,
            )
        except MissingAttributeError:
            return None

    @staticmethod
    def create_colourbar(
        lower_level: int,
        upper_level: int,
        colourmap_name: str,
    ) -> BytesIO:
        """
        Create a colour bar to visualise the chosen colour map and how the spread of
        colours has been adjusted using the lower and upper level settings.

        For simplicity, colour bars are 256 pixels wide allowing upper and lower level
        sliders to be placed alongside the image and each of the 256 settings to be
        chosen.
        The height of the colour bar is set in the config file.
        """
        image_array = [
            range(256) for _ in range(FalseColourHandler.colourbar_height_pixels)
        ]
        return FalseColourHandler.apply_false_colour(
            image_array,
            8,
            lower_level,
            upper_level,
            colourmap_name,
        )

    @staticmethod
    def apply_false_colour_to_b64_img(
        base64_image: str,
        lower_level: int,
        upper_level: int,
        colourmap_name: str,
    ) -> BytesIO:
        """
        Apply false colour to the image provided as a base 64 string. This is how the
        thumbnails are stored in the database.
        """
        img_src = PILImage.open(BytesIO(base64.b64decode(base64_image)))
        image_array = np.array(img_src)
        return FalseColourHandler.apply_false_colour(
            image_array,
            FalseColourHandler.get_pixel_depth(img_src),
            lower_level,
            upper_level,
            colourmap_name,
        )

    @staticmethod
    def apply_false_colour(
        image_array: np.ndarray,
        bits_per_pixel: int,
        lower_level: int,
        upper_level: int,
        colourmap_name: str,
    ) -> BytesIO:
        """
        Apply false colour to an image provided as a numpy array. An array can be
        converted regardless of the whether the original image was created in memory,
        retrieved as base 64 from the database, or from an image stored on disk.
        """
        if bits_per_pixel != 8 and bits_per_pixel != 16:
            raise ImageError(f"{bits_per_pixel} bits per pixel is not supported")
        else:
            pixel_multiplier = int((2**bits_per_pixel - 1) / 255)
        if lower_level is None:
            lower_level = 0
        if upper_level is None:
            upper_level = 255
        if upper_level < lower_level:
            raise QueryParameterError(
                "lower_level must be less than or equal to upperlevel",
            )
        # 8 bit images need the levels to be between 0 and 255
        # 16 bit images need the levels to be between 0 and 65525
        # the pixel multiplier adjusts for this
        lower_level = lower_level * pixel_multiplier
        upper_level = upper_level * pixel_multiplier
        if colourmap_name is None:
            colourmap_name = FalseColourHandler.default_colour_map_name
        if not ColourmapMapping.is_colourmap_available(
            FalseColourHandler.colourmap_names,
            colourmap_name,
        ):
            raise QueryParameterError(
                f"{colourmap_name} is not a valid colour map name",
            )

        converted_image_bytes = BytesIO()
        plt.imsave(
            converted_image_bytes,
            image_array,
            vmin=lower_level,
            vmax=upper_level,
            cmap=colourmap_name,
        )
        return converted_image_bytes

    @staticmethod
    def get_pixel_depth(image: PILImage) -> int:
        """
        Currently used to work out whether a greyscale image is an 8 or 16 bit image.
        May need to be extended later to handle colour images etc.
        """
        # See: https://pillow.readthedocs.io/en/stable/handbook/concepts.html#modes
        if image.mode == "L":
            # 8-bit black and white
            return 8
        elif image.mode == "I" or image.mode == "I;16":
            # as per the pillow docs these are 32-bit signed integer pixels
            # but for our usage these are 16 bit black and white images
            return 16
        else:
            raise ImageError(f"Image mode {image.mode} not recognised")
