import asyncio
from contextlib import asynccontextmanager
import logging

from elasticapm.contrib.starlette import ElasticAPM, make_apm_client
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import orjson
import uvicorn

from operationsgateway_api.src.config import Config
from operationsgateway_api.src.constants import LOG_CONFIG_LOCATION, ROUTE_MAPPINGS
import operationsgateway_api.src.experiments.runners as runners
from operationsgateway_api.src.experiments.unique_worker import (
    assign_event_to_single_worker,
    UniqueWorker,
)
from operationsgateway_api.src.mongo.connection import ConnectionInstance
from operationsgateway_api.src.routes import (
    auth,
    channels,
    experiments,
    export,
    filters,
    float_images,
    functions,
    images,
    ingest_data,
    maintenance,
    records,
    sessions,
    user_preferences,
    users,
    vectors,
    version,
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    ConnectionInstance()
    experiment_worker = UniqueWorker(Config.config.experiments.worker_file_path)

    @assign_event_to_single_worker(experiment_worker)
    async def get_experiments_on_startup():
        if Config.config.experiments.scheduler_background_task_enabled:
            log.info(
                "Creating task for Scheduler system to be contacted"
                " for experiment details",
            )
            asyncio.create_task(runners.scheduler_runner.start_task())
        else:
            log.info("Scheduler background task has not been enabled")

    await get_experiments_on_startup()

    if Config.config.backup is not None:
        backup_worker = UniqueWorker(Config.config.backup.worker_file_path)

        @assign_event_to_single_worker(backup_worker)
        async def backup():
            log.info("Creating task for XRootD backups")
            asyncio.create_task(runners.x_root_d_copy_runner.start_task())

        await backup()
    else:
        log.info("Backup task has not been enabled")

    yield

    experiment_worker.remove_file()
    if Config.config.backup is not None:
        backup_worker.remove_file()

    ConnectionInstance.db_connection.mongo_client.close()


app = FastAPI(
    title="OperationsGateway API",
    description=api_description,
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
    root_path=Config.config.app.url_prefix,
)

apm_config = {
    "ENVIRONMENT": Config.config.observability.environment,
    "SECRET_TOKEN": Config.config.observability.secret_key.get_secret_value(),
    "SERVER_URL": "http://localhost:8200",  # this should already be localhost
    "SERVICE_NAME": "operationsgateway",
    "ENABLED": True,
}

apm = make_apm_client(apm_config)

app.add_middleware(ElasticAPM, client=apm)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)


def setup_logger():
    libraries_info_logging = [
        "boto3",
        "botocore",
        "nose",
        "s3transfer",
        "matplotlib.font_manager",
        "zeep",
        "multipart",
    ]
    for name in libraries_info_logging:
        logging.getLogger(name).setLevel(logging.INFO)
    logging.config.fileConfig(LOG_CONFIG_LOCATION)


setup_logger()
log = logging.getLogger()
log.info("Logging now setup")


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
add_router_to_app(float_images.router)
add_router_to_app(ingest_data.router)
add_router_to_app(records.router)
add_router_to_app(waveforms.router)
add_router_to_app(vectors.router)
add_router_to_app(auth.router)
add_router_to_app(channels.router)
add_router_to_app(experiments.router)
add_router_to_app(export.router)
add_router_to_app(sessions.router)
add_router_to_app(user_preferences.router)
add_router_to_app(users.router)
add_router_to_app(functions.router)
add_router_to_app(filters.router)
add_router_to_app(maintenance.router)
add_router_to_app(version.router)

log.debug("ROUTE_MAPPINGS contents:")
for item in ROUTE_MAPPINGS.items():
    log.debug(item)


if __name__ == "__main__":
    uvicorn.run(
        "operationsgateway_api.src.main:app",
        host=Config.config.app.host,
        port=Config.config.app.port,
        reload=Config.config.app.reload,
        log_config=LOG_CONFIG_LOCATION,
    )
