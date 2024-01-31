from typing import Literal

from lark import Transformer
import numpy as np

from operationsgateway_api.src.functions.builtins.common import (
    centroid,
    type_check,
)


CENTROID_X_TOKEN = {
    "symbol": "centroid_x",
    "name": "Centroid (x)",
    "details": (
        "Calculate the x position of the centroid of an image. Errors if "
        "waveform or scalar provided. Implementation: Returns the x position "
        "of the image's centroid in terms of pixel values."
    ),
}


def centroid_x_type_check(self: Transformer, arguments: list) -> Literal["scalar"]:
    """
    Raises an error unless `arguments[0] in ["image"]`, and returns "scalar".
    """
    (argument,) = arguments
    return type_check(argument, ["image"], "scalar", "centroid_x")


def centroid_x(self: Transformer, arguments: list) -> float:
    """
    The first element of `arguments` must be a `np.ndarray`.

    Returns the x position of the image's centroid in terms of pixel values.
    """
    image = arguments[0]
    if not isinstance(image, np.ndarray):
        message = f"'centroid_x' accepts np.ndarray, {type(image)} provided"
        raise TypeError(message)

    return centroid(image, 0)
