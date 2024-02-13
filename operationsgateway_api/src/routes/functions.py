import logging

from fastapi import APIRouter, Depends, Query
from lark import LarkError, UnexpectedCharacters, UnexpectedEOF
from pydantic import Json
from typing_extensions import Annotated

from operationsgateway_api.src.auth.authorisation import authorise_token
from operationsgateway_api.src.error_handling import endpoint_error_handling
from operationsgateway_api.src.exceptions import FunctionParseError
from operationsgateway_api.src.functions import TOKENS, TypeTransformer


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

    return TOKENS


@router.get(
    "/functions",
    summary="Validate function",
    response_description=(
        "Checks the syntax, variable names and typing of the provided "
        "function, and returns the output type (scalar, waveform or image) of "
        "the function",
    ),
    responses={
        400: {"description": "The function was invalid"},
    },
    tags=["Functions"],
)
@endpoint_error_handling
async def validate_function(
    access_token: AuthoriseToken,
    function: Json = Query(
        description="Functions to evaluate on the record data being returned",
    ),
    function_types: Json = Query(
        default={},
        description=(
            "Return types of other functions upon which the expression depends"
        ),
    ),
):
    """
    Checks `expression` for Syntax and undefined variable errors.
    """
    log.info("Validating function")

    error = None
    transformer = TypeTransformer(function_types=function_types)
    expression = function["expression"]
    try:
        return_type = await transformer.evaluate(function["name"], expression)

    except ValueError as e:
        error = e.args[0]

    except UnexpectedEOF:
        error = (
            f"Unexpected end-of-input in '{expression}', check all brackets "
            "are closed"
        )

    except UnexpectedCharacters:
        error = f"Unexpected character in '{expression}', check all brackets are opened"

    except LarkError as e:
        message: str = e.args[0]
        root_message = message.split("\n\n")[1].strip('"')
        if 'Error trying to process rule "variable"' in message:
            error = f"Unexpected variable in '{expression}': {root_message}"
        elif "is not a recognised builtin function name" in message:
            error = f"Unsupported function in '{expression}': {root_message}"
        else:
            error = f"Unsupported type in '{expression}': {root_message}"

    finally:
        if error is not None:
            log.error(error)
            raise FunctionParseError(error)

    return return_type
