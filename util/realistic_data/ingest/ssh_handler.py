from io import BytesIO
from typing import List

from fabric import Connection
from util.realistic_data.ingest.config import Config


class SSHHandler:
    def __init__(self) -> None:
        self.connection = Connection(Config.config.script_options.ssh_connection_url)

    def transfer_experiments_file(self, experiments_file: BytesIO) -> None:
        self.connection.put(
            experiments_file,
            remote=Config.config.database.remote_experiments_file_path,
        )

    def import_experiments(self) -> None:
        self.connection.run(
            f"mongoimport --db='{Config.config.database.name}'"
            " --collection='experiments' --mode='upsert'"
            f" --file='{Config.config.database.remote_experiments_file_path}'",
        )
        self.connection.run(
            f"rm -f {Config.config.database.remote_experiments_file_path}",
        )

    def drop_database_collections(self, collection_names: List[str]) -> None:
        for collection_name in collection_names:
            print(
                f"Dropping collection '{collection_name}' in"
                f" {Config.config.database.name}",
            )
            self.connection.run(
                f"mongo --host {Config.config.database.hostname}"
                f" --port {Config.config.database.port} {Config.config.database.name}"
                f' --eval "db.{collection_name}.drop()"',
            )
