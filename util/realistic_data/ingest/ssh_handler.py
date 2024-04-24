from io import BytesIO
from typing import List

from fabric import Connection
from util.realistic_data.ingest.config import Config


class SSHHandler:
    def __init__(self) -> None:
        self.connection = Connection(Config.config.ssh.ssh_connection_url)

    def transfer_experiments_file(self, experiments_file: BytesIO) -> None:
        self.connection.put(
            experiments_file,
            remote=Config.config.database.remote_experiments_file_path,
        )

    def import_experiments(self) -> None:
        self.connection.run(
            f"mongoimport --collection='experiments' --mode='upsert'"
            f" --file='{Config.config.database.remote_experiments_file_path}'"
            f'"{Config.config.database.connection_uri}"'
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
                f'mongo "{Config.config.database.connection_uri}"'
                f' --eval "db.{collection_name}.drop()"',
            )
