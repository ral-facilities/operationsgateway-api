import logging
from typing import List

from fastapi import APIRouter, Depends
from lark import LarkError, UnexpectedCharacters, UnexpectedEOF
from typing_extensions import Annotated

from operationsgateway_api.src.auth.authorisation import authorise_token
from operationsgateway_api.src.error_handling import endpoint_error_handling
from operationsgateway_api.src.exceptions import FunctionParseError
from operationsgateway_api.src.functions import TOKENS, TypeTransformer
from operationsgateway_api.src.models import Function


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


@router.post(
    "/functions/validate",
    summary="Validate function",
    response_description=(
        "Checks the syntax, variable names and typing of the provided "
        "functions, and returns the output types (scalar, waveform or image) of "
        "the functions",
    ),
    responses={
        400: {"description": "A function was invalid"},
    },
    tags=["Functions"],
)
@endpoint_error_handling
async def validate_functions(
    access_token: AuthoriseToken,
    functions: List[Function],
) -> List[str]:
    """
    Checks the functions for Syntax and undefined variable errors. The functions
    provided are evaluated in order, so a function output used in the expression of
    another must be defined first. If an error is found, subsequent functions will not
    be evaluated.
    """
    log.info("Validating functions")

    return_types = []
    error = None
    transformer = TypeTransformer()
    for i, function_model in enumerate(functions):
        try:
            return_type = await transformer.evaluate(
                function_model.name,
                function_model.expression,
            )
            return_types.append(return_type)

        except ValueError as e:
            error = e.args[0]

        except UnexpectedEOF:
            error = (
                f"expression '{function_model.expression}' has unexpected end-of-input,"
                " check all brackets are closed"
            )

        except UnexpectedCharacters:
            error = (
                f"expression '{function_model.expression}' has unexpected character,"
                " check all brackets are opened"
            )

        except LarkError as e:
            # Remove the Lark header on what rule was being executed and just
            # return the original error message we raised
            message: str = e.args[0]
            error = message.split("\n\n")[1].strip('"')

        finally:
            if error is not None:
                log.error(error)
                raise FunctionParseError(f"Error at index {i}: {error}")

    return return_types
