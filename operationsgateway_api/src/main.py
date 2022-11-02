import logging

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import orjson
import uvicorn

from operationsgateway_api.src.config import Config
from operationsgateway_api.src.logger_config import setup_logger
from operationsgateway_api.src.mongo.connection import ConnectionInstance
from operationsgateway_api.src.routes import (
    auth,
    experiments,
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

setup_logger()
log = logging.getLogger()
log.info("Logging now setup")


@app.on_event("startup")
async def startup_mongodb_client():
    ConnectionInstance()


@app.on_event("shutdown")
async def close_mongodb_client():
    ConnectionInstance.db_connection.mongo_client.close()


# Adding endpoints to FastAPI app
app.include_router(images.router)
app.include_router(ingest_data.router)
app.include_router(records.router)
app.include_router(waveforms.router)
app.include_router(auth.router)
app.include_router(experiments.router)

if __name__ == "__main__":
    uvicorn.run(
        "operationsgateway_api.src.main:app",
        host=Config.config.app.host,
        port=Config.config.app.port,
        reload=Config.config.app.reload,
        access_log=False,
    )
