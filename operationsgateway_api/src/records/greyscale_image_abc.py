from __future__ import annotations

from io import BytesIO
import logging

import numpy as np
from PIL import Image as PILImage
from pydantic import Json

from operationsgateway_api.src.auth.jwt_handler import JwtHandler
from operationsgateway_api.src.config import Config
from operationsgateway_api.src.functions.builtins.centroid_x import CentroidX
from operationsgateway_api.src.functions.builtins.centroid_y import CentroidY
from operationsgateway_api.src.functions.builtins.fwhm import FWHM
from operationsgateway_api.src.functions.variable_models import WaveformVariable
from operationsgateway_api.src.models import ImageModel
from operationsgateway_api.src.records.false_colour_handler import FalseColourHandler
from operationsgateway_api.src.records.image_abc import ImageABC
from operationsgateway_api.src.records.thumbnail_handler import ThumbnailHandler

log = logging.getLogger()


class GreyscaleImageABC(ImageABC):
    """
    Base for the image types whose stored pixels are one 8 or 16 bit intensity value,
    which is `Image` and `ImageSeries`.
    """

    lookup_table_16_to_8_bit = [i / 256 for i in range(65536)]

    def __init__(self, image: ImageModel) -> None:
        super().__init__(image)

        self._normalise_bit_depth()

    def _normalise_bit_depth(self) -> None:
        """
        Prepare `self.image.data` for storage at either 8 or 16 bits.

        Data is only ever stored as 8 or 16 bit, so data with any other bit depth is
        shifted into the most significant bits. So a full scale 12 bit pixel is
        also full scale once stored, rather than looking dim in a 16 bit container.
        ImageModel.bit_depth` keeps the originally specified depth.
        """
        if isinstance(self.image.bit_depth, int):
            bit_depth = self.image.bit_depth
            if bit_depth <= 8 and self.image.data.dtype != np.uint8:
                msg = (
                    "Specified bit depth is lower than actual bit depth with dtype "
                    "of %s, only data in the %s least significant bits will be kept"
                )
                log.warning(msg, self.image.data.dtype, bit_depth)
            elif bit_depth > 16:
                log.warning(
                    "Specified bit depth is higher than the max supported depth of 16, "
                    "only data in the 16 most significant bits will be kept",
                )
        else:
            if self.image.data.dtype == np.uint8:
                bit_depth = 8
            else:
                # In principle this could be data with any number of bits, but we have
                # no way of knowing without an explicit bit_depth so default to 16
                bit_depth = 16

        # We only store data as either 8 or 16 bit PNGs, scale to most significant bits
        if bit_depth <= 8:
            target_bit_depth = 8
            target_dtype = np.uint8
        else:
            target_bit_depth = 16
            target_dtype = np.uint16

        self.image.data = self.image.data.astype(target_dtype)
        shifted_data = self.image.data * 2 ** (target_bit_depth - bit_depth)
        # Negative shifts may result in a float output, so cast the type again
        self.image.data = shifted_data.astype(target_dtype)

    def _create_greyscale_thumbnail(self, data: np.ndarray) -> None:
        """
        Create a thumbnail from `data`, a 2D 8 or 16 bit greyscale array, and store
        it as an attribute of this object.

        Shared by the image types that store greyscale data, which differ only in
        which array they take the thumbnail from.
        """

        log.info("Creating image thumbnail for %s", self.image.path)

        # Opening image then saving in a bytes object before using that to open and
        # generate a thumbnail as you can't produce a thumbnail when opening the image
        # using `fromarray()`
        image_bytes = BytesIO()
        img_temp = PILImage.fromarray(data)
        img_temp.save(image_bytes, format="PNG")

        img = PILImage.open(image_bytes)
        # Images of a certain mode must be converted to mode I to avoid a ValueError
        # where PIL complains the image is in the wrong mode
        if img.mode == "I;16":
            img = img.convert("I")

        img.thumbnail(Config.config.images.thumbnail_size)
        # convert 16 bit greyscale thumbnails to 8 bit to save space
        if img.mode == "I":
            log.debug("Converting 16 bit greyscale thumbnail to 8 bit")
            img = img.point(GreyscaleImageABC.lookup_table_16_to_8_bit, "L")
        self.thumbnail = ThumbnailHandler.convert_to_base64(img)

        img.close()

    @staticmethod
    def apply_false_colour(
        image_bytes: bytes,
        original_image: bool,
        lower_level: int,
        upper_level: int,
        limit_bit_depth: int,
        colourmap_name: str,
    ) -> bytes:
        """
        If not requesting the `original_image`, then false colour will be applied to
        `image_bytes` using the other parameters.
        """
        if original_image:
            log.debug("Original image requested, return unmodified image bytes")
            return image_bytes
        else:
            log.debug("False colour requested, applying false colour to image")
            img_src = PILImage.open(BytesIO(image_bytes))
            orig_img_array = np.array(img_src)
            storage_bit_depth = FalseColourHandler.get_pixel_depth(img_src)
            false_colour_image = FalseColourHandler.apply_false_colour(
                image_array=orig_img_array,
                storage_bit_depth=storage_bit_depth,
                lower_level=lower_level,
                upper_level=upper_level,
                limit_bit_depth=limit_bit_depth,
                colourmap_name=colourmap_name,
            )
            img_src.close()
            return false_colour_image.getvalue()

    @staticmethod
    async def get_preferred_colourmap(access_token: str) -> str:
        """
        Check the user's database record to see if they have a preferred colour map set
        """
        username = JwtHandler.get_payload(access_token)["username"]
        colourmap_name = await FalseColourHandler.get_preferred_colourmap(username)
        log.debug("Preferred colour map for %s is %s", username, colourmap_name)
        return colourmap_name

    @staticmethod
    def validate_position(position: Json, orig_img_array: np.ndarray) -> "tuple[int]":
        """If position is undefined, then the centroid of the `orig_img_array`
        will be calculated and returned.
        """
        if position is None:
            position_x = CentroidX.evaluate(orig_img_array)
            position_y = CentroidY.evaluate(orig_img_array)
            position = int(position_x), int(position_y)

        return position

    @staticmethod
    def extract_image_intensity(position: int, array: np.ndarray) -> dict:
        """Converts a row or column from an image (at `position`) into a
        Waveform and calculates the FWHM for display in the UI.
        """
        waveform = WaveformVariable(x=np.arange(len(array)), y=array)
        waveform_model = waveform.to_waveform_model()
        fwhm = float(FWHM.evaluate(waveform=waveform))
        return {"position": position, "intensity": waveform_model, "fwhm": fwhm}
