import logging

from cexprtk import check_expression, ParseException
from fastapi import APIRouter, Depends, Query, Response, status
from typing_extensions import Annotated

from operationsgateway_api.src.auth.authorisation import (
    authorise_token,
)
from operationsgateway_api.src.error_handling import endpoint_error_handling
from operationsgateway_api.src.exceptions import FunctionParseError


log = logging.getLogger()
router = APIRouter()
AuthoriseToken = Annotated[str, Depends(authorise_token)]


@router.get(
    "/functions/tokens",
    summary="Get all supported function tokens",
    response_description="List of function tokens",
    tags=["Functions"],
)
@endpoint_error_handling
async def get_function_tokens(
    access_token: AuthoriseToken,
):
    """
    Returns all tokens that are understood by the function parser. This includes
    operators (+, -, etc.) and functions (max, min, etc.) but not symbols for
    variables, which is dependent on the defined channels and is therefore not static.
    """

    log.info("Getting function tokens")

    # TODO will probably need help text as well as just the symbols
    # mathematical_operators = [
    #     "+", "-", "*", "/", "%", "^", "(", ")"
    # ]
    # functions = ["avg", "exp", "max", "min", "log"]

    # TODO NYI
    # TODO include implementation details for complex functions
    # unknown_functions = [
    #     "centre",
    #     "fwhm",
    #     "integration",
    #     "falling",
    #     "rising",
    #     "background",
    # ]

    return [
        {"symbol": "+", "name": "Add"},
        {"symbol": "-", "name": "Subtract"},
        {"symbol": "*", "name": "Multiply"},
        {"symbol": "/", "name": "Divide"},
        {"symbol": "%", "name": "Remainder (modular division)"},
        {"symbol": "^", "name": "Raise to power"},
        {"symbol": "(", "name": "Open bracket"},
        {"symbol": ")", "name": "Close bracket"},
        {
            "symbol": "avg",
            "name": "Mean",
            "details": (
                "Calculate the mean of a trace (using the y variable) or image input. "
                "No effect on a scalar input."
            ),
        },
        {
            "symbol": "exp",
            "name": "Exponential",
            "details": (
                "Raise `e` to the power of the input argument (element-wise if a trace "
                "or image is provided)."
            ),
        },
        {
            "symbol": "log",
            "name": "Natural logarithm",
            "details": (
                "Calculate the logarithm in base `e` of the input argument "
                "(element-wise if a trace or image is provided)."
            ),
        },
        {
            "symbol": "max",
            "name": "Maximum",
            "details": (
                "Calculate the maximum value in a trace (using the y variable) or "
                "image input. No effect on a scalar input."
            ),
        },
        {
            "symbol": "min",
            "name": "Minimum",
            "details": (
                "Calculate the minimum value in a trace (using the y variable) or "
                "image input. No effect on a scalar input."
            ),
        },
    ]


@router.get(
    "/functions",
    summary="Validate function",
    response_description="200 OK (no response body) if the function is valid",
    responses={
        400: {"description": "The function was invalid"},
    },
    tags=["Functions"],
)
@endpoint_error_handling
async def validate_function(
    access_token: AuthoriseToken,
    expression: str = Query(
        description="Function to validate",
    ),
):
    """
    Checks `expression` for Syntax, but not undefined Symbol errors.
    """

    log.info("Validating function")

    # TODO handle recursion here? would require us to submit multiple functions...
    # TODO check we get useful information back for the user
    try:
        check_expression(expression)
    except ParseException as e:
        raise FunctionParseError(str(e)) from e

    return Response(status_code=status.HTTP_200_OK)
