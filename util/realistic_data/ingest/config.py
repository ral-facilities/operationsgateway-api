from enum import Enum
from pathlib import Path
import sys
from typing import Optional

from pydantic import BaseModel, ValidationError
import yaml


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


class Echo(BaseModel):
    endpoint_url: str
    access_key: str
    secret_key: str
    simulated_data_bucket: str
    storage_bucket: str
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


class IngestEchoDataConfig(BaseModel):
    script_options: ScriptOptions
    database: Database
    echo: Echo
    api: API

    @classmethod
    def load(cls, path=Path(__file__).parent.parent / "config.yml"):
        try:
            with open(path, encoding="utf-8") as config_file:
                config = yaml.safe_load(config_file)
                return cls(**config)
        except (IOError, ValidationError, yaml.YAMLError) as e:
            sys.exit(f"An error occurred while loading the config data: {e}")


class Config:
    config = IngestEchoDataConfig.load()
