from typing import Literal

from lark import Transformer
import numpy as np

from operationsgateway_api.src.functions.builtins.common import smooth, type_check
from operationsgateway_api.src.functions.waveform_variable import WaveformVariable


INTEGRATE_TOKEN = {
    "symbol": "integrate",
    "name": "Integrate",
    "details": (
        "Integrate a waveform or image. Errors if scalar provided. "
        "Implementation (waveform): First, applies smoothing by taking weighted "
        "nearest and next-nearest neighbour contributions to y values whose "
        "difference from their neighbours is more than 0.2 times the total "
        "range in y. The y values are then integrated with respect to x, with "
        "the last y value neglected."
        "Implementation (image): Return the sum of all pixel values."
    ),
}


def integrate_type_check(self: Transformer, arguments: list) -> Literal["scalar"]:
    """
    Raises an error unless `arguments in ["waveform", "image"]`, and returns "scalar".
    """
    (argument,) = arguments
    return type_check(argument, ["waveform", "image"], "scalar", "integrate")


def integrate(self: Transformer, arguments: list) -> float:
    """
    The first element of `arguments` must be a `WaveformVariable` or `np.ndarray`.

    Waveform:
    First, applies smoothing by taking weighted nearest and next-nearest
    neighbour contributions to  y values whose difference from their neighbours
    is more than 0.2 times the total range in y.
    The y values are then integrated with respect to x, with the last y value
    neglected.

    Image:
    Return the sum of all pixel values.
    """
    argument = arguments[0]
    if isinstance(argument, WaveformVariable):
        smooth(argument.y)
        return np.sum(argument.y[:-1] * np.diff(argument.x))
    elif isinstance(argument, np.ndarray):
        return np.sum(argument)
    else:
        message = (
            "'integrate' accepts [WaveformVariable, np.ndarray], "
            f"{type(argument)} provided"
        )
        raise TypeError(message)
