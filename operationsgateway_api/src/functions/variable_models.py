import numpy as np

from operationsgateway_api.src.models import (
    PartialImageChannelModel,
    PartialScalarChannelModel,
    PartialWaveformChannelModel,
    WaveformModel,
)
from operationsgateway_api.src.records.waveform import Waveform


class WaveformVariable:
    def __init__(
        self,
        waveform_model: WaveformModel = None,
        x: np.ndarray = None,
        y: np.ndarray = None,
        x_units: str = None,
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

        # We do not operate on the x axis, so these units will preserved.
        # In general, the y_units may change so do not persist these.
        self.x_units = x_units

    def __str__(self) -> str:
        return f"y:\n{self.y}\nx:\n{self.x}"

    def __add__(self, other) -> "WaveformVariable":
        return self.to_new_waveform_variable(self.y + other)

    __radd__ = __add__

    def __sub__(self, other) -> "WaveformVariable":
        return self.to_new_waveform_variable(self.y - other)

    def __rsub__(self, other) -> "WaveformVariable":
        return self.to_new_waveform_variable(other - self.y)

    def __mul__(self, other) -> "WaveformVariable":
        return self.to_new_waveform_variable(self.y * other)

    __rmul__ = __mul__

    def __truediv__(self, other) -> "WaveformVariable":
        return self.to_new_waveform_variable(self.y / other)

    def __rtruediv__(self, other) -> "WaveformVariable":
        return self.to_new_waveform_variable(other / self.y)

    def __pow__(self, other) -> "WaveformVariable":
        return self.to_new_waveform_variable(self.y**other)

    def __rpow__(self, other) -> "WaveformVariable":
        return self.to_new_waveform_variable(other**self.y)

    # Define reductive functions to act on y and return a float
    def min(self, **kwargs) -> float:  # noqa: A003
        return np.min(self.y, **kwargs)

    def max(self, **kwargs) -> float:  # noqa: A003
        return np.max(self.y, **kwargs)

    def mean(self, **kwargs) -> float:
        return np.mean(self.y, **kwargs)

    # Define element-wise functions to act on y and return WaveformVariable
    def exp(self) -> "WaveformVariable":
        return self.to_new_waveform_variable(np.exp(self.y))

    def log(self) -> "WaveformVariable":
        return self.to_new_waveform_variable(np.log(self.y))

    # Utility methods
    def to_new_waveform_variable(self, y: np.ndarray) -> "WaveformVariable":
        return WaveformVariable(x=self.x.copy(), y=y, x_units=self.x_units)

    def to_waveform(self) -> Waveform:
        return Waveform(self.to_waveform_model())

    def to_waveform_model(self) -> WaveformModel:
        return WaveformModel(_id="_", x=self.x, y=self.y)


class PartialWaveformVariableChannelModel(PartialWaveformChannelModel):
    variable_value: WaveformVariable  # Arbitrary type used to track variable internally
    data: WaveformModel | None = None

    class Config:
        arbitrary_types_allowed = True


class PartialImageVariableChannelModel(PartialImageChannelModel):
    variable_value: np.ndarray  # Arbitrary type used to track variable internally
    data: bytes | None = None

    class Config:
        arbitrary_types_allowed = True


PartialVariableChannelModel = (
    PartialImageVariableChannelModel
    | PartialScalarChannelModel
    | PartialWaveformVariableChannelModel
)


PartialVariableChannels = dict[str, PartialVariableChannelModel]
