from abc import ABC, abstractmethod

import numpy as np

from operationsgateway_api.src.functions.variable_models import WaveformVariable


class Builtin(ABC):
    @property
    @abstractmethod
    def input_types(self) -> "set[str]":
        """The channel types accepted by this builtin"""

    @property
    @abstractmethod
    def output_type(self) -> str:
        """The channel type output by this builtin"""

    @property
    @abstractmethod
    def symbol(self) -> str:
        """The symbol used to represent this builtin in an expression"""

    @property
    @abstractmethod
    def token(self) -> "dict[str, str]":
        """`dict` containing all help and implementation details"""

    @staticmethod
    @abstractmethod
    def evaluate(
        argument: "float | WaveformVariable | np.ndarray",
    ) -> "float | WaveformVariable | np.ndarray":
        """Actually evaluate the builtin on a single numeric argument"""

    @staticmethod
    def centroid(image: np.ndarray, axis: int) -> int:
        """
        Calculates the centre of mass
        """
        sums = np.sum(image, axis=axis)
        weighted_sums = sums * np.arange(len(sums))
        centre_of_mass = np.sum(weighted_sums) / np.sum(sums)
        return int(centre_of_mass)

    @staticmethod
    def calculate_fwhm(waveform: WaveformVariable) -> "tuple[float, float]":
        """
        First, applies smoothing by taking weighted nearest and next-nearest
        neighbour contributions to  y values whose difference from their neighbours
        is more than 0.2 times the total range in y. The maximum y value is then
        identified along with the x positions bounding the FWHM.
        """
        y = waveform.y
        Builtin.smooth(y)

        y -= np.min(y)
        max_y = np.max(y)
        half_max_left_i = half_max_right_i = max_i = np.argmax(y)
        low_values_left = np.where(y[:max_i] <= max_y / 2)[0]
        low_values_right = np.where(y[max_i:] <= max_y / 2)[0]

        if len(low_values_left):
            half_max_left_i = low_values_left[-1]

        if len(low_values_right):
            half_max_right_i = low_values_right[0] + max_i

        return waveform.x[half_max_left_i], waveform.x[half_max_right_i]

    @staticmethod
    def smooth(y: np.ndarray) -> None:
        """
        Applies smoothing by taking weighted nearest and next-nearest
        neighbour contributions to  y values whose difference from their neighbours
        is more than 0.2 times the total range in y.

        Note that this modifies y in place.
        """
        diff_tolerance = (np.max(y) - np.min(y)) * 0.2
        diff = np.diff(y)

        length = len(y)
        if length >= 3:
            if (
                abs(diff[0]) > diff_tolerance
                and abs(diff[0] + diff[1]) > diff_tolerance
            ):
                y[0] += (3 * diff[0] + diff[1]) / 6

            for i in range(1, length - 1):
                if abs(diff[i - 1]) > diff_tolerance and abs(diff[i]) > diff_tolerance:
                    correction = -2 * diff[i - 1] + 2 * diff[i]
                    divisor = 7
                    if i > 1:
                        correction -= diff[i - 2] + diff[i - 1]
                        divisor += 1
                    if i < length - 2:
                        correction += diff[i] + diff[i + 1]
                        divisor += 1

                    y[i] += correction / divisor

            if (
                abs(diff[-1]) > diff_tolerance
                and abs(diff[-1] + diff[-2]) > diff_tolerance
            ):
                y[-1] -= (3 * diff[-1] + diff[-2]) / 6

    @classmethod
    def type_check(cls, argument_type: str) -> None:
        """Raises a TypeError with a human readable message detailed the
        provided and acceptable types to this function.

        Args:
            argument (str): Argument provided.

        Raises:
            TypeError: Formatted with input and acceptable types.
        """
        if argument_type not in cls.input_types:
            raise TypeError(
                f"'{cls.symbol}' accepts {cls.input_types} type(s), "
                f"'{argument_type}' provided",
            )

    @classmethod
    def evaluation_type_check(
        cls,
        argument: "float | WaveformVariable | np.ndarray",
    ) -> None:
        """Raises a TypeError with a human readable message detailed the
        provided and acceptable types to this function from an actual value
        provided at evaluation.

        Args:
            argument (float | WaveformVariable | np.ndarray): Argument provided.

        Raises:
            TypeError: Formatted with input and acceptable types.
        """
        types_dict = {
            float: "scalar",
            WaveformVariable: "waveform",
            np.ndarray: "image",
        }
        cls.type_check(types_dict.get(type(argument), type(argument).__name__))
