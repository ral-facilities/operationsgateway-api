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
    default_float_colour_map_name = Config.config.float_images.default_colour_map
    colourbar_height_pixels = Config.config.images.colourbar_height_pixels
    preferred_colour_map_pref_name = Config.config.images.preferred_colour_map_pref_name
    preferred_float_colour_map_pref_name = (
        Config.config.float_images.preferred_colour_map_pref_name
    )
    colourmap_names = ColourmapMapping.get_colourmap_mappings()

    @staticmethod
    async def get_preferred_colourmap(username: str) -> str:
        """
        Check whether the user has stored a preference for which colour map they prefer
        to use. Return the value if they have, otherwise return None.
        """
        try:
            pref_name = FalseColourHandler.preferred_colour_map_pref_name
            return await UserPreferences.get(username, pref_name)
        except MissingAttributeError:
            return FalseColourHandler.default_colour_map_name

    @staticmethod
    async def get_preferred_float_colourmap(username: str) -> str:
        """
        Check whether the user has stored a preference for which colour map they prefer
        to use for float images. Return the value if they have, otherwise return
        None.
        """
        try:
            pref_name = FalseColourHandler.preferred_float_colour_map_pref_name
            return await UserPreferences.get(username, pref_name)
        except MissingAttributeError:
            return FalseColourHandler.default_float_colour_map_name

    @staticmethod
    def create_colourbar(
        lower_level: int,
        upper_level: int,
        limit_bit_depth: int,
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
            image_array=image_array,
            storage_bit_depth=8,
            lower_level=lower_level,
            upper_level=upper_level,
            limit_bit_depth=limit_bit_depth,
            colourmap_name=colourmap_name,
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
            lower_level=lower_level,
            upper_level=upper_level,
            limit_bit_depth=8,  # All thumbnails are 8 bit, so limits should be too
            colourmap_name=colourmap_name,
        )

    @staticmethod
    def apply_false_colour_to_b64_float_img(
        base64_image: str,
        colourmap_name: str,
    ) -> BytesIO:
        """
        Apply false colour to a float image provided as a base 64 string. This is how
        the thumbnails are stored in the database.

        Null values are tracked by an alpha channel value of 0, so need to extract the
        already normalised L channel and apply colour to whilst persisting alpha.
        """
        img_src = PILImage.open(BytesIO(base64.b64decode(base64_image)))
        image_array = np.array(img_src)
        values = image_array[:, :, 0]
        alpha = image_array[:, :, 1]
        colourmap = plt.cm.get_cmap(colourmap_name)
        mapped_array = colourmap(values, alpha=alpha, bytes=True)
        converted_image_bytes = BytesIO()
        plt.imsave(converted_image_bytes, mapped_array)

        return converted_image_bytes

    @staticmethod
    def apply_false_colour(
        image_array: np.ndarray,
        storage_bit_depth: int,
        lower_level: int,
        upper_level: int,
        limit_bit_depth: int,
        colourmap_name: str,
    ) -> BytesIO:
        """
        Apply false colour to an image provided as a numpy array. An array can be
        converted regardless of the whether the original image was created in memory,
        retrieved as base 64 from the database, or from an image stored on disk.
        """
        vmin, vmax = FalseColourHandler.pixel_limits(
            storage_bit_depth=storage_bit_depth,
            lower_level=lower_level,
            upper_level=upper_level,
            limit_bit_depth=limit_bit_depth,
        )
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
            vmin=vmin,
            vmax=vmax,
            cmap=colourmap_name,
        )
        return converted_image_bytes

    @staticmethod
    def apply_false_colour_float(
        image_array: np.ndarray,
        absolute_max: float,
        colourmap_name: str,
    ) -> BytesIO:
        """
        Apply false colour to a float image provided as a numpy array. To preserve
        position of 0 at the centre of the colourmap, the absolute_max pixel value is
        used to set both vmin and vmax.
        """
        if colourmap_name is None:
            colourmap_name = FalseColourHandler.default_float_colour_map_name
        if not ColourmapMapping.is_colourmap_available(
            FalseColourHandler.colourmap_names,
            colourmap_name,
        ):
            msg = f"{colourmap_name} is not a valid colour map name"
            raise QueryParameterError(msg)

        converted_image_bytes = BytesIO()
        plt.imsave(
            converted_image_bytes,
            image_array,
            vmin=-absolute_max,
            vmax=absolute_max,
            cmap=colourmap_name,
        )
        return converted_image_bytes

    @staticmethod
    def pixel_limits(
        storage_bit_depth: int,
        lower_level: int,
        upper_level: int,
        limit_bit_depth: int,
    ) -> "tuple[int, int]":
        """Adjusts pixel limits to account for the bit depth the image was actually
        saved with.

        Args:
            storage_bit_depth (int):
                Bit depth of each pixel in the stored format, such that the max value is
                `2**actual_bit_depth - 1`
            lower_level (int): Low pixel value in `limit_bit_depth`
            upper_level (int): High pixel value in `limit_bit_depth`
            limit_bit_depth (int): The bit depth used for the limit levels provided

        Raises:
            QueryParameterError:
                If `lower_level` is greater than `upper_level` or `upper_level` is
                greater than or equal to 2**`limit_bit_depth`.

        Returns:
            tuple[int, int]: The scaled limits
        """

        if lower_level is None:
            lower_level = 0

        if upper_level is None:
            upper_level = 2**limit_bit_depth - 1
        elif upper_level >= 2**limit_bit_depth:
            msg = "upper_level must be less than 2**limit_bit_depth"
            raise QueryParameterError(msg)

        if upper_level < lower_level:
            raise QueryParameterError(
                "lower_level must be less than or equal to upperlevel",
            )

        pixel_multiplier = 2 ** (storage_bit_depth - limit_bit_depth)
        vmin = lower_level * pixel_multiplier
        vmax = (upper_level + 1) * pixel_multiplier - 1
        return vmin, vmax

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
