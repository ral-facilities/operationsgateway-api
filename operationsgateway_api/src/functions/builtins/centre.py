from typing import Literal

from lark import Transformer

from operationsgateway_api.src.functions.builtins.common import (
    calculate_fwhm,
    type_check,
)
from operationsgateway_api.src.functions.waveform_variable import WaveformVariable


CENTRE_TOKEN = {
    "symbol": "centre",
    "name": "Centre",
    "details": (
        "Calculate the centre of a waveform. Errors if image or scalar "
        "provided. Implementation: First, applies smoothing by taking weighted "
        "nearest and next-nearest neighbour contributions to  y values whose "
        "difference from their neighbours is more than 0.2 times the total "
        "range in y. The maximum y value is then identified along with the x "
        "positions bounding the FWHM, and x value at the centre of this region "
        "is returned. Note this will not be the same as the x value of the "
        "maximum, unless the data is symmetric."
    ),
}


def centre_type_check(self: Transformer, arguments: list) -> Literal["scalar"]:
    """
    Raises an error unless `argument[0] in ["waveform"]`, and returns "scalar".
    """
    (argument,) = arguments
    return type_check(argument, ["waveform"], "scalar", "centre")


def centre(self: Transformer, arguments: list) -> float:
    """
    The first element of `arguments` must be a `WaveformVariable`.

    First, applies smoothing by taking weighted nearest and next-nearest
    neighbour contributions to  y values whose difference from their neighbours
    is more than 0.2 times the total range in y. The maximum y value is then
    identified along with the x positions bounding the FWHM, and x value at the
    centre of this region is returned. Note this will not be the same as the x
    value of the maximum, unless the data is symmetric."
    """
    waveform = arguments[0]
    if not isinstance(waveform, WaveformVariable):
        message = f"'centre' accepts WaveformVariable, {type(waveform)} provided"
        raise TypeError(message)

    half_max_left, half_max_right = calculate_fwhm(waveform)
    return (half_max_left + half_max_right) / 2