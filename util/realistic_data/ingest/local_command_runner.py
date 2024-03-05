from io import BytesIO
from os import path
from subprocess import Popen
from time import sleep
from typing import List

from util.realistic_data.ingest.config import Config


class LocalCommandRunner:
    def store_experiments_file(self, experiments_file: BytesIO) -> None:
        binary_file = open(Config.config.database.remote_experiments_file_path, "wb")
        binary_file.write(experiments_file.getvalue())
        binary_file.close()

        file_exists = False
        while not file_exists:
            file_exists = path.isfile(
                Config.config.database.remote_experiments_file_path,
            )
            print(
                f"{Config.config.database.remote_experiments_file_path} hasn't been"
                " created yet..",
            )
            sleep(1)

        print(
            f"Written '{Config.config.database.remote_experiments_file_path}' to file",
        )

    def import_experiments(self) -> None:
        Popen(
            [
                "mongoimport",
                f"--db={Config.config.database.name}",
                "--collection=experiments",
                "--mode=upsert",
                f"--file={Config.config.database.remote_experiments_file_path}",
            ],
        )

    def drop_database_collections(self, collection_names: List[str]) -> None:
        for collection_name in collection_names:
            print(
                f"Dropping collection '{collection_name}' in"
                f" {Config.config.database.name}",
            )
            Popen(
                [
                    "mongo",
                    "--host",
                    Config.config.database.hostname,
                    "--port",
                    str(Config.config.database.port),
                    Config.config.database.name,
                    "--eval",
                    f"db.{collection_name}.drop()",
                ],
            )
