import logging
from pathlib import Path
from typing import BinaryIO

from operationsgateway_api.src.config import Config
from operationsgateway_api.src.models import RecordModel
from operationsgateway_api.src.records.echo_interface import EchoInterface


log = logging.getLogger()


class XRootDClient:
    @staticmethod
    def cache_hdf(record_model: RecordModel, buffer: BinaryIO) -> None:
        """
        Cache the bytes in `buffer` to a path on local storage corresponding to the id
        of `record_model`. This can then be copied to tape at a later time, decoupled
        from the ingest to Echo.
        """
        if Config.config.backup is not None:
            directory = Config.config.backup.cache_directory
            subdirectories = EchoInterface.format_record_id(record_model.id_)
            version = record_model.version
            log.debug("Writing %s version %s to cache", record_model.id_, version)
            file = Path(f"{directory}/{subdirectories}/{version}.hdf5")
            file.parent.mkdir(parents=True, exist_ok=True)
            buffer.seek(0)
            with open(file, "wb") as f:
                f.write(buffer.read())
