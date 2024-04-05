import logging
from typing import List

from fastapi import APIRouter, Depends, Path, Query
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
) -> list:
    """
    Returns all tokens that are understood by the function parser. This includes
    operators (+, -, etc.) and functions (max, min, etc.) but not symbols for
    variables, which is dependent on the defined channels and is therefore not static.
    """

    log.info("Getting function tokens")

    return TOKENS


@router.get(
    "/functions/validate/{function_name}",
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
    function_name: Annotated[
        str,
        Path(
            ...,
            description="Name identifying the function to validate",
        ),
    ],
    functions: List[Json] = Query(
        description="All functions upon which the named function might depend",
    ),
) -> str:
    """
    Checks the named function for Syntax and undefined variable errors.
    """
    log.info("Validating function")

    error = None
    transformer = TypeTransformer()
    for function_dict in functions:
        expression = function_dict["expression"]

        try:
            return_type = await transformer.evaluate(function_dict["name"], expression)
            if function_dict["name"] == function_name:
                return return_type

        except ValueError as e:
            error = e.args[0]

        except UnexpectedEOF:
            error = (
                f"Unexpected end-of-input in '{expression}', check all brackets "
                "are closed"
            )

        except UnexpectedCharacters:
            error = (
                f"Unexpected character in '{expression}', check all brackets are opened"
            )

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

    raise FunctionParseError(f"No function defined with name {function_name}")
