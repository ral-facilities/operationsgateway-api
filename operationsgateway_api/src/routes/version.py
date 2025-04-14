from importlib.metadata import version
import logging

from fastapi import APIRouter

from operationsgateway_api.src.error_handling import endpoint_error_handling

log = logging.getLogger()
router = APIRouter()


@router.get(
    "/version",
    summary="Gets the deployed version of the API",
    response_description="A tag to identify the GIT release",
    tags=["Version"],
)
@endpoint_error_handling
async def get_version():
    # The version is set in the pyproject.toml
    return {"version": version("operationsgateway-api")}
