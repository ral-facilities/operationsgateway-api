from typing import Literal

from lark import Transformer
import numpy as np

from operationsgateway_api.src.functions.builtins.centroid_y import centroid_y
from operationsgateway_api.src.functions.builtins.common import (
    calculate_fwhm,
    type_check,
)
from operationsgateway_api.src.functions.waveform_variable import WaveformVariable


FWHM_X_TOKEN = {
    "symbol": "fwhm_x",
    "name": "Full Width Half Maximum (x)",
    "details": (
        "Calculate the FWHM of an image across the x axis, at the y position "
        "of the image centroid. Errors if waveform or scalar "
        "provided. Implementation: First, calculates the centroid and extracts "
        "the y position. Then applies smoothing by taking weighted "
        "nearest and next-nearest neighbour contributions to pixel values whose "
        "difference from their neighbours is more than 0.2 times the total "
        "range in values. The maximum value is then identified along with the "
        "positions bounding the FWHM and the distance in pixels returned."
    ),
}


def fwhm_x_type_check(self: Transformer, arguments: list) -> Literal["scalar"]:
    """
    Raises an error unless `arguments[0] in ["image"]`, and returns "scalar".
    """
    (argument,) = arguments
    return type_check(argument, ["image"], "scalar", "fwhm_x")


def fwhm_x(self: Transformer, arguments: list) -> float:
    """
    The first element of `arguments` must be a `WaveformVariable`.

    First, calculates the centroid and extracts the y position. Then applies
    smoothing by taking weighted nearest and next-nearest neighbour
    contributions to pixel values whose difference from their neighbours is more
    than 0.2 times the total range in values. The maximum value is then
    identified along with the positions bounding the FWHM and the distance in
    pixels returned.
    """
    image = arguments[0]
    if not isinstance(image, np.ndarray):
        message = f"'fwhm_x' accepts np.ndarray, {type(image)} provided"
        raise TypeError(message)

    centroid_position = centroid_y(None, [image])
    y = image[centroid_position]
    waveform_variable = WaveformVariable(x=np.array(range(len(y))), y=y)

    half_max_left, half_max_right = calculate_fwhm(waveform_variable)
    return half_max_right - half_max_left
