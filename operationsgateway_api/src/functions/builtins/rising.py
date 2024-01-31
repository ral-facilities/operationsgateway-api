from typing import Literal

from lark import Transformer

from operationsgateway_api.src.functions.builtins.common import (
    calculate_fwhm,
    type_check,
)
from operationsgateway_api.src.functions.waveform_variable import WaveformVariable


RISING_TOKEN = {
    "symbol": "rising",
    "name": "Rising",
    "details": (
        "Calculate the rising edge of a waveform. Errors if image or scalar "
        "provided. Implementation: First, applies smoothing by taking weighted "
        "nearest and next-nearest neighbour contributions to  y values whose "
        "difference from their neighbours is more than 0.2 times the total "
        "range in y. The maximum y value is then identified along with the x "
        "positions bounding the FWHM and the lower x value is returned."
    ),
}


def rising_type_check(self: Transformer, arguments: list) -> Literal["scalar"]:
    """
    Raises an error unless `arguments[0] in ["waveform"]`, and returns "scalar".
    """
    (argument,) = arguments
    return type_check(argument, ["waveform"], "scalar", "rising")


def rising(self: Transformer, arguments: list) -> float:
    """
    The first element of `arguments` must be a `WaveformVariable`.

    First, applies smoothing by taking weighted nearest and next-nearest
    neighbour contributions to  y values whose difference from their neighbours
    is more than 0.2 times the total range in y. The maximum y value is then
    identified along with the x positions bounding the FWHM and the lowerd x
    value is returned.
    """
    waveform = arguments[0]
    if not isinstance(waveform, WaveformVariable):
        message = f"'rising' accepts WaveformVariable, {type(waveform)} provided"
        raise TypeError(message)

    half_max_left, _ = calculate_fwhm(waveform)
    return half_max_left
