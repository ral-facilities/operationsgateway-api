from operationsgateway_api.src.functions.builtins.builtins import Builtins

TOKENS = [
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
            "Calculate the mean of a waveform (using the y variable) or image "
            "input. No effect on a scalar input. Implementation: "
            "https://numpy.org/doc/stable/reference/generated/numpy.mean.html"
        ),
    },
    {
        "symbol": "exp",
        "name": "Exponential",
        "details": (
            "Raise `e` to the power of the input argument (element-wise if a "
            "waveform or image is provided). Implementation: "
            "https://numpy.org/doc/stable/reference/generated/numpy.exp.html"
        ),
    },
    {
        "symbol": "log",
        "name": "Natural logarithm",
        "details": (
            "Calculate the logarithm in base `e` of the input argument "
            "(element-wise if a waveform or image is provided). Implementation:"
            "https://numpy.org/doc/stable/reference/generated/numpy.log.html"
        ),
    },
    {
        "symbol": "max",
        "name": "Maximum",
        "details": (
            "Calculate the maximum value in a waveform (using the y variable) or "
            "image input. No effect on a scalar input. Implementation: "
            "https://numpy.org/doc/stable/reference/generated/numpy.max.html"
        ),
    },
    {
        "symbol": "min",
        "name": "Minimum",
        "details": (
            "Calculate the minimum value in a waveform (using the y variable) or "
            "image input. No effect on a scalar input. Implementation: "
            "https://numpy.org/doc/stable/reference/generated/numpy.min.html"
        ),
    },
    *Builtins.tokens,
]
