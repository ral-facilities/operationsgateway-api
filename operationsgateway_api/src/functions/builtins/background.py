import numpy as np

from operationsgateway_api.src.functions.builtins.builtin import Builtin
from operationsgateway_api.src.functions.waveform_variable import WaveformVariable


class Background(Builtin):
    input_types = {"waveform", "image"}
    output_type = "scalar"
    symbol = "background"
    token = {
        "symbol": symbol,
        "name": "Background",
        "details": (
            "Calculate the background of a waveform or image. Errors if scalar "
            "provided. "
            "Implementation (waveform): First, applies smoothing by taking "
            "weighted nearest and next-nearest neighbour contributions to y "
            "values whose difference from their neighbours is more than 0.2 "
            "times the total range in y. The first 25 and last 25 y values in "
            "the signal are averaged to give an estimate of the background."
            "Implementation (image): The average pixel value in the 10 by 10 region "
            "in the top left of the image is returned."
        ),
    }

    @staticmethod
    def evaluate(argument: "WaveformVariable | np.ndarray") -> float:
        """
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
        if isinstance(argument, WaveformVariable):
            Builtin.smooth(argument.y)
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
