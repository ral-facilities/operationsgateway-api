import logging

from fastapi import FastAPI
import uvicorn

from operationsgateway_api.src.config import Config
from operationsgateway_api.src.logger_config import setup_logger
from operationsgateway_api.src.mongo.connection import ConnectionInstance
from operationsgateway_api.src.routes import images, ingest_data, records, waveforms


app = FastAPI()

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

if __name__ == "__main__":
    uvicorn.run(
        "operationsgateway_api.src.main:app",
        host=Config.config.app.host,
        port=Config.config.app.port,
        reload=Config.config.app.reload,
        access_log=False,
    )
