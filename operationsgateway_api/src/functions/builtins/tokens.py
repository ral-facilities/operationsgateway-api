from operationsgateway_api.src.functions.builtins.background import BACKGROUND_TOKEN
from operationsgateway_api.src.functions.builtins.centre import CENTRE_TOKEN
from operationsgateway_api.src.functions.builtins.centroid_x import CENTROID_X_TOKEN
from operationsgateway_api.src.functions.builtins.centroid_y import CENTROID_Y_TOKEN
from operationsgateway_api.src.functions.builtins.falling import FALLING_TOKEN
from operationsgateway_api.src.functions.builtins.fwhm import FWHM_TOKEN
from operationsgateway_api.src.functions.builtins.fwhm_x import FWHM_X_TOKEN
from operationsgateway_api.src.functions.builtins.fwhm_y import FWHM_Y_TOKEN
from operationsgateway_api.src.functions.builtins.integrate import INTEGRATE_TOKEN
from operationsgateway_api.src.functions.builtins.rising import RISING_TOKEN

tokens = [
    {"symbol": "+", "name": "Add"},
    {"symbol": "-", "name": "Subtract"},
    {"symbol": "*", "name": "Multiply"},
    {"symbol": "/", "name": "Divide"},
    {"symbol": "**", "name": "Raise to power"},
    {"symbol": "(", "name": "Open bracket"},
    {"symbol": ")", "name": "Close bracket"},
    {
        "symbol": "mean",
        "name": "Mean",
        "details": (
            "Calculate the mean of a trace (using the y variable) or image "
            "input. No effect on a scalar input. Implementation: "
            "https://numpy.org/doc/stable/reference/generated/numpy.mean.html"
        ),
    },
    {
        "symbol": "exp",
        "name": "Exponential",
        "details": (
            "Raise `e` to the power of the input argument (element-wise if a "
            "trace or image is provided). Implementation: "
            "https://numpy.org/doc/stable/reference/generated/numpy.exp.html"
        ),
    },
    {
        "symbol": "log",
        "name": "Natural logarithm",
        "details": (
            "Calculate the logarithm in base `e` of the input argument "
            "(element-wise if a trace or image is provided). Implementation:"
            "https://numpy.org/doc/stable/reference/generated/numpy.log.html"
        ),
    },
    {
        "symbol": "max",
        "name": "Maximum",
        "details": (
            "Calculate the maximum value in a trace (using the y variable) or "
            "image input. No effect on a scalar input. Implementation: "
            "https://numpy.org/doc/stable/reference/generated/numpy.max.html"
        ),
    },
    {
        "symbol": "min",
        "name": "Minimum",
        "details": (
            "Calculate the minimum value in a trace (using the y variable) or "
            "image input. No effect on a scalar input. Implementation: "
            "https://numpy.org/doc/stable/reference/generated/numpy.min.html"
        ),
    },
    BACKGROUND_TOKEN,
    CENTRE_TOKEN,
    CENTROID_X_TOKEN,
    CENTROID_Y_TOKEN,
    FALLING_TOKEN,
    FWHM_X_TOKEN,
    FWHM_Y_TOKEN,
    FWHM_TOKEN,
    INTEGRATE_TOKEN,
    RISING_TOKEN,
]
