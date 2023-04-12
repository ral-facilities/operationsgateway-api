import logging.config
from pathlib import Path

from operationsgateway_api.src.config import Config

LOG_FILE_NAME = Path(Config.config.logging.log_location)

log_message_location = (
    " {%(module)s:%(filename)s:%(funcName)s:%(lineno)d} "
    if Config.config.logging.log_message_location
    else " "
)
log_format = f"[%(asctime)s]{log_message_location}%(levelname)s - %(message)s"

# TODO 2 - try to move to a rotating file handler, while still keeping FastAPI output
# into both file and stdout
logger_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": log_format,
        },
    },
    "handlers": {
        "default": {
            "level": Config.config.logging.log_level,
            "formatter": "default",
            "class": "logging.FileHandler",
            "filename": LOG_FILE_NAME,
        },
    },
    "loggers": {"uvicorn.access": {"handlers": ["default"]}},
    "root": {"level": Config.config.logging.log_level, "handlers": ["default"]},
}


def setup_logger():
    libraries_info_logging = [
        "boto3",
        "botocore",
        "nose",
        "s3transfer",
        "matplotlib.font_manager",
    ]
    for name in libraries_info_logging:
        logging.getLogger(name).setLevel(logging.INFO)

    logging.config.dictConfig(logger_config)
