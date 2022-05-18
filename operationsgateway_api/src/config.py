from pathlib import Path
import sys
from typing import Optional

from pydantic import (
    BaseModel,
    StrictBool,
    StrictInt,
    StrictStr,
    ValidationError,
)
import yaml


class App(BaseModel):
    """Configuration model class to store configuration regarding the FastAPI app"""

    # TODO - create wsgi/asgi.py so the following is true
    # Some options aren't mandatory when running the API in the production
    host: Optional[StrictStr]
    port: Optional[StrictInt]
    reload: Optional[StrictBool]


class Logging(BaseModel):
    """Configuration model class to store configuration of logging"""

    log_level: StrictStr
    log_location: StrictStr
    log_message_location: StrictBool


class MongoDB(BaseModel):
    """Configuration model class to store MongoDB configuration details"""

    mongodb_url: StrictStr
    database_name: StrictStr
    collection_name: StrictStr
    max_documents: StrictInt


class APIConfig(BaseModel):
    """
    Class to store the API's configuration settings
    """

    app: App
    logging: Logging
    mongodb: MongoDB

    @classmethod
    def load(cls, path=Path(__file__).parent.parent / "config.yml"):  # noqa: B008
        """
        Load the config data from the .yml file and store it as a dict
        """

        try:
            with open(path, encoding="utf-8") as config_file:
                config = yaml.safe_load(config_file)
                return cls(**config)
        except (IOError, ValidationError, yaml.YAMLError) as e:
            sys.exit(f"An error occurred while loading the config data: {e}")


class Config:
    """Class containing config as a class variable so it can mocked during testing"""

    config = APIConfig.load()
