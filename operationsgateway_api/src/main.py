import logging

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import orjson
import uvicorn

from operationsgateway_api.src.config import Config
from operationsgateway_api.src.constants import ROUTE_MAPPINGS
from operationsgateway_api.src.logger_config import setup_logger
from operationsgateway_api.src.mongo.connection import ConnectionInstance
from operationsgateway_api.src.routes import (
    auth,
    images,
    ingest_data,
    records,
    waveforms,
)


# Add custom response class to deal with NaN values ingested into MongoDB
# https://github.com/ral-facilities/operationsgateway-api/pull/9 explains the reasoning
# behind this change
class ORJSONResponse(JSONResponse):
    media_type = "application/json"

    def render(self, content) -> bytes:
        return orjson.dumps(content)


api_description = """
This API is the backend to OperationsGateway that allows users to:
- Ingest HDF files containing scalar, image and waveform data into a MongoDB instance
- Query MongoDB to get records containing data channels, using typical database filters
- Get waveform data and full-size images via specific endpoints
"""

app = FastAPI(
    title="OperationsGateway API",
    description=api_description,
    default_response_class=ORJSONResponse,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

setup_logger()
log = logging.getLogger()
log.info("Logging now setup")


@app.on_event("startup")
async def startup_mongodb_client():
    ConnectionInstance()


@app.on_event("shutdown")
async def close_mongodb_client():
    ConnectionInstance.db_connection.mongo_client.close()


def add_router_to_app(api_router: APIRouter):
    # add this router to the FastAPI app
    app.include_router(api_router)
    # add an entry for each of the routes (endpoints) in that router to a dictionary
    # that maps the function for the endpoint to the endpoint "path" and "method" eg.
    # <function get_full_image at 0x7...9d0>, '/images/{record_id}/{channel_name} GET'
    # so that the mappings can be used for authorisation
    for route in api_router.routes:
        ROUTE_MAPPINGS[route.endpoint] = f"{route.path} {list(route.methods)[0]}"


# Adding endpoints to FastAPI app
add_router_to_app(images.router)
add_router_to_app(ingest_data.router)
add_router_to_app(records.router)
add_router_to_app(waveforms.router)
add_router_to_app(auth.router)

log.debug("ROUTE_MAPPINGS contents:")
for item in ROUTE_MAPPINGS.items():
    log.debug(item)


if __name__ == "__main__":
    uvicorn.run(
        "operationsgateway_api.src.main:app",
        host=Config.config.app.host,
        port=Config.config.app.port,
        reload=Config.config.app.reload,
        access_log=False,
    )
