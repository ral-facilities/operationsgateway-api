import numpy as np

from operationsgateway_api.src.functions.builtins.builtin import Builtin


class CentroidY(Builtin):
    input_types = {"image"}
    output_type = "scalar"
    symbol = "centroid_y"
    token = {
        "symbol": symbol,
        "name": "Centroid (y)",
        "details": (
            "Calculate the y position of the centroid of an image. Errors if "
            "waveform or scalar provided. Implementation: Returns the y position "
            "of the image's centroid in terms of pixels."
        ),
    }

    @staticmethod
    def evaluate(image: np.ndarray) -> float:
        """
        Calculate the y position of the centroid of an image. Errors if waveform or
        scalar provided.

        Returns the y position of the image's centroid in terms of pixels.
        """
        return Builtin.centroid(image, 1)
