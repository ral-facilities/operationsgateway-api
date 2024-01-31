from typing import Literal

import numpy as np

from operationsgateway_api.src.functions.waveform_variable import WaveformVariable


def type_check(
    argument: str,
    accepted: list[str],
    return_type: str,
    function: str,
) -> Literal["scalar"]:
    """
    Raises an error unless `argument == accepted`, and returns `return_type`.
    """
    if argument not in accepted:
        message = f"'{function}' accepts {accepted} type(s), '{argument}' provided"
        raise TypeError(message)
    return return_type


def centroid(image: np.ndarray, axis: int):
    """
    Calculates the centre of mass
    """
    sums = np.sum(image, axis=axis)
    weighted_sums = sums * range(len(sums))
    centre_of_mass = np.sum(weighted_sums) / np.sum(sums)
    return int(centre_of_mass)


def calculate_fwhm(waveform: WaveformVariable):
    """
    First, applies smoothing by taking weighted nearest and next-nearest
    neighbour contributions to  y values whose difference from their neighbours
    is more than 0.2 times the total range in y. The maximum y value is then
    identified along with the x positions bounding the FWHM.
    """
    y = waveform.y
    smooth(y)

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
        if abs(diff[0]) > diff_tolerance and abs(diff[0] + diff[1]) > diff_tolerance:
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

        if abs(diff[-1]) > diff_tolerance and abs(diff[-1] + diff[-2]) > diff_tolerance:
            y[-1] -= (3 * diff[-1] + diff[-2]) / 6
