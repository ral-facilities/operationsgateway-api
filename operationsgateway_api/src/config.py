from datetime import datetime
from pathlib import Path
import sys
from typing import Optional, Tuple

from dateutil import tz
from pydantic import (
    BaseModel,
    field_validator,
    StrictBool,
    StrictInt,
    StrictStr,
    ValidationError,
)
import yaml


class App(BaseModel):
    """Configuration model class to store configuration regarding the FastAPI app"""

    # Some options aren't mandatory when running the API in the production
    host: Optional[StrictStr] = None
    port: Optional[StrictInt] = None
    reload: Optional[StrictBool] = None


class ImagesConfig(BaseModel):
    # The dimensions will be stored as a list in the YAML file, but are cast to tuple
    # using `typing.Tuple` because this is the type used by Pillow
    image_thumbnail_size: Tuple[int, int]
    waveform_thumbnail_size: Tuple[int, int]
    # the system default colour map (used if no user preference is set)
    default_colour_map: StrictStr
    colourbar_height_pixels: StrictInt
    preferred_colour_map_pref_name: StrictStr


class MongoDB(BaseModel):
    """Configuration model class to store MongoDB configuration details"""

    mongodb_url: StrictStr
    database_name: StrictStr
    max_documents: StrictInt
    image_store_directory: StrictStr


class AuthConfig(BaseModel):
    """Configuration model class to store authentication configuration details"""

    private_key_path: StrictStr
    public_key_path: StrictStr
    jwt_algorithm: StrictStr
    access_token_validity_mins: StrictInt
    refresh_token_validity_days: StrictInt
    fedid_server_url: StrictStr
    fedid_server_ldap_realm: StrictStr


class ExperimentsConfig(BaseModel):
    """Configuration model class to store experiment configuration details"""

    first_scheduler_contact_start_date: datetime
    scheduler_background_task_enabled: StrictBool
    scheduler_background_frequency: StrictStr
    scheduler_background_timezone: StrictStr
    scheduler_background_retry_mins: float
    user_office_wsdl_url: StrictStr
    username: StrictStr
    password: StrictStr
    scheduler_wsdl_url: StrictStr
    instrument_name: StrictStr
    worker_file_path: StrictStr

    @field_validator("scheduler_background_timezone")
    @classmethod
    def check_timezone(cls, value):  # noqa: B902, N805
        if not tz.gettz(value):
            sys.exit(f"scheduler_background_timezone is not a valid timezone: {value}")
        else:
            return value


class APIConfig(BaseModel):
    """
    Class to store the API's configuration settings
    """

    # When in production, there's no `app` section in the config file. A default value
    # (i.e. an empty instance of `App`) has been assigned so that if the code attempts
    # to access a config value in this section, an error is prevented
    app: Optional[App] = App()
    mongodb: MongoDB
    auth: AuthConfig
    experiments: ExperimentsConfig
    images: ImagesConfig

    @classmethod
    def load(cls, path=Path(__file__).parent.parent / "config.yml"):
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
