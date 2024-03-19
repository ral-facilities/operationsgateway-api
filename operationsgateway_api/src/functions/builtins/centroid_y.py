import numpy as np

from operationsgateway_api.src.functions.builtins.builtin import Builtin


class CentroidY(Builtin):
    input_types = {"image"}
    output_type = "scalar"
    symbol = "centroid_y"
    token = {
        "symbol": symbol,
        "name": "Centroid (Y)",
        "details": (
            "Calculate the y position of the centroid of an image. Errors if "
            "waveform or scalar provided. Implementation: Returns the y position "
            "of the image's centroid in terms of pixel values."
        ),
    }

    @staticmethod
    def evaluate(image: np.ndarray) -> float:
        """
        Returns the y position of the image's centroid in terms of pixel values.
        """
        return Builtin.centroid(image, 1)
