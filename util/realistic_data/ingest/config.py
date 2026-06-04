from enum import Enum
from pathlib import Path
from typing import Optional, Tuple, Type

from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)


class IngestModeEnum(str, Enum):
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"


class ScriptOptions(BaseModel):
    wipe_database: bool
    wipe_echo: bool
    launch_api: bool
    import_users: bool
    ingest_mode: IngestModeEnum
    file_to_restart_ingestion: Optional[str]


class Database(BaseModel):
    connection_uri: str
    remote_experiments_file_path: str
    test_users_file_path: str


class SourceConfig(BaseModel):
    endpoint_url: str
    access_key: SecretStr
    secret_key: SecretStr
    simulated_data_bucket: str
    page_size: int


class API(BaseModel):
    https: bool
    host: str
    port: int
    username: str
    password: str
    log_config_path: str
    gunicorn_num_workers: str
    timeout_seconds: int
    storage_bucket: str = Field(
        description=(
            "Bucket used for storage by the API when running. Should correspond to "
            "`echo.bucket_name` in the main `config.yaml`. Only used if "
            "`script_options.wipe_echo` is True, in which case entire contents of the "
            "bucket will be deleted."
        ),
        examples=["og-yourname-dev"],
    )


class IngestEchoDataConfig(BaseSettings):
    script_options: ScriptOptions
    database: Database
    source: SourceConfig
    api: API

    model_config = SettingsConfigDict(
        yaml_file=Path(__file__).parent.parent / "config.yml",
        env_nested_delimiter="__",
        hide_input_in_errors=True,
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls),
            file_secret_settings,
        )
