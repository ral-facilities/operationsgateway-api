import numpy as np

from operationsgateway_api.src.models import WaveformModel
from operationsgateway_api.src.records.waveform import Waveform


class WaveformVariable:
    def __init__(
        self,
        waveform_model: WaveformModel = None,
        x: np.ndarray = None,
        y: np.ndarray = None,
    ) -> None:
        """
        Create a object that can handle mathematical operations from either
        `waveform_model` or explicit `x` and `y` values.
        """
        if x is not None and y is not None:
            self.x = x.astype(float)
            self.y = y.astype(float)
        elif waveform_model is not None:
            self.y = np.array(waveform_model.y)
            self.x = np.array(waveform_model.x)
        else:
            raise ValueError("No arguments provided to __init__")

    def __str__(self) -> str:
        return f"y:\n{self.y}\nx:\n{self.x}"

    def __add__(self, other) -> "WaveformVariable":
        return WaveformVariable(x=self.x.copy(), y=self.y + other)

    __radd__ = __add__

    def __sub__(self, other) -> "WaveformVariable":
        return WaveformVariable(x=self.x.copy(), y=self.y - other)

    def __rsub__(self, other) -> "WaveformVariable":
        return WaveformVariable(x=self.x.copy(), y=other - self.y)

    def __mul__(self, other) -> "WaveformVariable":
        return WaveformVariable(x=self.x.copy(), y=self.y * other)

    __rmul__ = __mul__

    def __truediv__(self, other) -> "WaveformVariable":
        return WaveformVariable(x=self.x.copy(), y=self.y / other)

    def __rtruediv__(self, other) -> "WaveformVariable":
        return WaveformVariable(x=self.x.copy(), y=other / self.y)

    def __pow__(self, other) -> "WaveformVariable":
        return WaveformVariable(x=self.x.copy(), y=self.y**other)

    def __rpow__(self, other) -> "WaveformVariable":
        return WaveformVariable(x=self.x.copy(), y=other**self.y)

    # Define reductive functions to act on y and return a float
    def min(self, **kwargs) -> float:  # noqa: A003
        return np.min(self.y, **kwargs)

    def max(self, **kwargs) -> float:  # noqa: A003
        return np.max(self.y, **kwargs)

    def mean(self, **kwargs) -> float:
        return np.mean(self.y, **kwargs)

    # Define element-wise functions to act on y and return WaveformVariable
    def exp(self) -> "WaveformVariable":
        return WaveformVariable(x=self.x.copy(), y=np.exp(self.y))

    def log(self) -> "WaveformVariable":
        return WaveformVariable(x=self.x.copy(), y=np.log(self.y))

    # Utility methods
    def to_waveform(self) -> Waveform:
        return Waveform(self.to_waveform_model())

    def to_waveform_model(self) -> Waveform:
        return WaveformModel(_id="_", x=self.x, y=self.y)
