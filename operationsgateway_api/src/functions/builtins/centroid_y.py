from typing import Literal

from lark import Transformer
import numpy as np

from operationsgateway_api.src.functions.builtins.common import (
    centroid,
    type_check,
)

CENTROID_Y_TOKEN = {
    "symbol": "centroid_y",
    "name": "Centroid (y)",
    "details": (
        "Calculate the y position of the centroid of an image. Errors if "
        "waveform or scalar provided. Implementation: Returns the y position "
        "of the image's centroid in terms of pixel values."
    ),
}


def centroid_y_type_check(self: Transformer, arguments: list) -> Literal["scalar"]:
    """
    Raises an error unless `arguments[0] in ["image"]`, and returns "scalar".
    """
    (argument,) = arguments
    return type_check(argument, ["image"], "scalar", "centroid_y")


def centroid_y(self: Transformer, arguments: list) -> float:
    """
    The first element of `arguments` must be a `np.ndarray`.

    Returns the y position of the image's centroid in terms of pixel values.
    """
    image = arguments[0]
    if not isinstance(image, np.ndarray):
        message = f"'centroid_y' accepts np.ndarray, {type(image)} provided"
        raise TypeError(message)

    return centroid(image, 1)
