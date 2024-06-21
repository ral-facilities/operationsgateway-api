from datetime import datetime
import json
from typing import List

from dateutil import parser
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.uri_parser import parse_uri
from util.realistic_data.ingest.config import Config


class DatabaseOperations:
    def __init__(self) -> None:
        # Async client allows insert_many() to work as an upsert, simplfying
        # implementation of import_data()
        self.client = AsyncIOMotorClient(Config.config.database.connection_uri)
        self.db = self.client[self.get_database_name()]

    def get_database_name(self) -> str:
        return parse_uri(Config.config.database.connection_uri)["database"]

    def drop_collections(self, collection_names: List[str]) -> None:
        for collection_name in collection_names:
            self.db.drop_collection(collection_name)

    def import_data(self, file_path: str, collection_name: str) -> None:
        with open(file_path) as f:
            data = []
            for line in f.readlines():
                json_line = json.loads(line)
                for k, v in json_line.items():
                    # Converting `$date` used for mongoimport into datetimes so they're
                    # stored in the database as dates, not strings
                    if isinstance(v, dict) and list(v.keys())[0] == "$date":
                        json_line[k] = parser.isoparse(v["$date"])
                data.append(json_line)

        collection = getattr(self.db, collection_name)
        collection.insert_many(data)
        print(f"Imported {len(data)} documents to {collection_name} collection")

    def is_collection_empty(self, collection_name: str):
        collection = getattr(self.db, collection_name)
        count = collection.count_documents()
        print(f"count: {count}, type: {type(count)}")
