import numpy as np

from operationsgateway_api.src.functions.builtins.builtin import Builtin
from operationsgateway_api.src.functions.waveform_variable import WaveformVariable


class Integrate(Builtin):
    input_types = {"waveform", "image"}
    output_type = "scalar"
    symbol = "integrate"
    token = {
        "symbol": symbol,
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

    @staticmethod
    def evaluate(argument: "WaveformVariable | np.ndarray") -> float:
        """
        Integrate a waveform or image. Errors if scalar provided.

        Waveform:
        First, applies smoothing by taking weighted nearest and next-nearest
        neighbour contributions to  y values whose difference from their neighbours
        is more than 0.2 times the total range in y.
        The y values are then integrated with respect to x, with the last y value
        neglected.

        Image:
        Return the sum of all pixel values.
        """
        if isinstance(argument, WaveformVariable):
            Builtin.smooth(argument.y)
            return np.sum(argument.y[:-1] * np.diff(argument.x))
        elif isinstance(argument, np.ndarray):
            return np.sum(argument)
        else:
            # The check will fail and raise a TypeError
            Integrate.evaluation_type_check(argument)
