from typing import Literal

from lark import Transformer
import numpy as np

from operationsgateway_api.src.functions.builtins.common import smooth, type_check
from operationsgateway_api.src.functions.waveform_variable import WaveformVariable


BACKGROUND_TOKEN = {
    "symbol": "background",
    "name": "Background",
    "details": (
        "Calculate the background of a waveform or image. Errors if scalar "
        "provided. Implementation (waveform): First, applies smoothing by taking "
        "weighted nearest and next-nearest neighbour contributions to  y values whose "
        "difference from their neighbours is more than 0.2 times the total "
        "range in y. The first 25 and last 25 y values in the signal are "
        "averaged to give an estimate of the background."
        "Implementation (image): The average pixel value in the 10 by 10 region "
        "in the top left of the image is returned."
    ),
}


def background_type_check(self: Transformer, arguments: list) -> Literal["scalar"]:
    """
    Raises an error unless `arguments in ["waveform", "image"]`, and returns "scalar".
    """
    (argument,) = arguments
    return type_check(argument, ["waveform", "image"], "scalar", "background")


def background(self: Transformer, arguments: list) -> float:
    """
    The first element of `arguments` must be a `WaveformVariable` or `np.ndarray`.

    Waveform:
    First, applies smoothing by taking weighted nearest and next-nearest
    neighbour contributions to  y values whose difference from their neighbours
    is more than 0.2 times the total range in y.
    The first 25 and last 25 y values in the signal are averaged to give an
    estimate of the background.

    Image:
    The average pixel value in the 10 by 10 region in the top left of the image
    is returned.
    """
    argument = arguments[0]
    if isinstance(argument, WaveformVariable):
        smooth(argument.y)
        if len(argument.y) < 50:
            return np.mean(argument.y)
        else:
            return (np.mean(argument.y[:25]) + np.mean(argument.y[-25:])) / 2
    elif isinstance(argument, np.ndarray):
        return np.mean(argument[:10, :10])
    else:
        message = (
            "'background' accepts [WaveformVariable, np.ndarray], "
            f"{type(argument)} provided"
        )
        raise TypeError(message)
