import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from operationsgateway_api.src.config import Config
from operationsgateway_api.src.error_handling import endpoint_error_handling

log = logging.getLogger()
router = APIRouter()


@router.get(
    "/version",
    summary="Gets the deployed version hash of the API",
    response_description="A hash to identify the GIT release",
    tags=["Version"],
)
@endpoint_error_handling
async def get_version():
    version = Config.config.app.version
    log.info("Returning API version: %s", version)
    return JSONResponse(content={"version": version})
