from datetime import datetime
from pathlib import Path
import sys
from typing import Annotated, List, Optional, Tuple

import annotated_types
from dateutil import tz
from pydantic import (
    BaseModel,
    DirectoryPath,
    Field,
    field_validator,
    FilePath,
    NonNegativeInt,
    PositiveInt,
    SecretStr,
    StrictBool,
    StrictInt,
    StrictStr,
    ValidationError,
)
from xrootd_utils.common import AutoRemove
import yaml


class App(BaseModel):
    """Configuration model class to store configuration regarding the FastAPI app"""

    # Some options aren't mandatory when running the API in the production
    host: Optional[StrictStr] = None
    port: Optional[StrictInt] = None
    reload: Optional[StrictBool] = None
    url_prefix: StrictStr
    maintenance_file: FilePath
    scheduled_maintenance_file: FilePath


class ImagesConfig(BaseModel):
    # The dimensions will be stored as a list in the YAML file, but are cast to tuple
    # using `typing.Tuple` because this is the type used by Pillow
    thumbnail_size: Tuple[int, int]
    # the system default colour map (used if no user preference is set)
    default_colour_map: StrictStr
    colourbar_height_pixels: StrictInt
    preferred_colour_map_pref_name: StrictStr


class FloatImagesConfig(BaseModel):
    thumbnail_size: tuple[int, int]
    default_colour_map: StrictStr
    preferred_colour_map_pref_name: StrictStr


class WaveformsConfig(BaseModel):
    thumbnail_size: Tuple[int, int]
    line_width: float


class VectorsConfig(BaseModel):
    thumbnail_size: tuple[int, int]
    skip_pref_name: StrictStr = "VECTOR_SKIP"
    limit_pref_name: StrictStr = "VECTOR_LIMIT"


class EchoConfig(BaseModel):
    url: StrictStr
    username: StrictStr
    access_key: SecretStr
    secret_key: SecretStr
    bucket_name: StrictStr
    expiry_days: PositiveInt | None = Field(
        default=None,
        description="If defined, objects older than this will be marked for expiry",
        examples=[1095],
    )
    cache_maxsize: NonNegativeInt = 128


class MongoDB(BaseModel):
    """Configuration model class to store MongoDB configuration details"""

    mongodb_url: SecretStr
    database_name: StrictStr
    max_documents: StrictInt


class OidcProviderConfig(BaseModel):
    configuration_url: StrictStr
    audience: StrictStr
    verify_cert: StrictBool
    mechanism: StrictStr
    matching_claim: StrictStr


class AuthConfig(BaseModel):
    """Configuration model class to store authentication configuration details"""

    private_key_path: StrictStr
    public_key_path: StrictStr
    jwt_algorithm: StrictStr
    access_token_validity_mins: StrictInt
    refresh_token_validity_days: StrictInt
    fedid_server_url: StrictStr
    fedid_server_ldap_realm: StrictStr
    oidc_providers: dict[StrictStr, OidcProviderConfig] = {}


class ExperimentsConfig(BaseModel):
    """Configuration model class to store experiment configuration details"""

    first_scheduler_contact_start_date: datetime
    scheduler_background_task_enabled: StrictBool
    scheduler_background_frequency: StrictStr
    scheduler_background_timezone: StrictStr
    scheduler_background_retry_mins: float
    user_office_rest_api_url: StrictStr
    username: StrictStr
    password: SecretStr
    scheduler_wsdl_url: StrictStr
    instrument_names: List[StrictStr]
    worker_file_path: StrictStr

    @field_validator("scheduler_background_timezone")
    @classmethod
    def check_timezone(cls, value):  # noqa: B902, N805
        if not tz.gettz(value):
            sys.exit(f"scheduler_background_timezone is not a valid timezone: {value}")
        else:
            return value


class ExportConfig(BaseModel):
    """Configuration model class to store export configuration details"""

    max_filesize_bytes: StrictInt


class ObservabilityConfig(BaseModel):
    """Configuration model class to store export observability details"""

    environment: StrictStr
    secret_key: SecretStr  # apm key


class BackupConfig(BaseModel):
    cache_directory: DirectoryPath = Field(
        description=(
            "Directory to write incoming files to so that they can later be backed up "
            "to tape."
        ),
        examples=["/srv/og-api/cache"],
    )
    warning_mark_percent: Annotated[PositiveInt, annotated_types.Lt(100)] = Field(
        default=50,
        description=(
            "Above this level of disk usage for the cache_directory, log warnings"
        ),
    )
    target_url: StrictStr = Field(
        description="XRootD URL defining the server and root directory path to copy to",
        examples=["root://localhost:1094//path/to/directory/"],
    )
    copy_cron_string: StrictStr = Field(
        description="Cron string defining the schedule of the backup tasks",
        examples=["0 * * * *", "0 18 * * 1-5"],
    )
    timezone_str: StrictStr = Field(
        default="Europe/London",
        description="String to pass to Cron for determining the schedule",
    )
    worker_file_path: StrictStr = Field(
        description="Path of file used to ensure back is only handled by one worker.",
        examples=["/home/user/backup_worker"],
    )
    auto_remove: AutoRemove = Field(
        default=AutoRemove.BACKED_UP,
        description=(
            "Under what condition to remove local file copies: when there is a copy in "
            "the XRootD cache, when it is backed up to tape, or never."
        ),
        examples=["cached", "backed_up", "never"],
    )


class APIConfig(BaseModel):
    """
    Class to store the API's configuration settings
    """

    # When in production, there's no `app` section in the config file. A default value
    # (i.e. an empty instance of `App`) has been assigned so that if the code attempts
    # to access a config value in this section, an error is prevented
    app: App
    mongodb: MongoDB
    auth: AuthConfig
    experiments: ExperimentsConfig
    images: ImagesConfig
    float_images: FloatImagesConfig
    waveforms: WaveformsConfig
    vectors: VectorsConfig
    echo: EchoConfig
    export: ExportConfig
    observability: ObservabilityConfig
    backup: BackupConfig | None = None

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
