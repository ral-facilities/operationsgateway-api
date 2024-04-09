from bson import ObjectId
from pymongo import MongoClient
import pytest

from operationsgateway_api.src.config import Config
from operationsgateway_api.src.exceptions import DatabaseError


@pytest.fixture()
def single_favourite_filter():
    test_filter = FavouriteFilter()
    inserted_filter = test_filter.create_one()

    yield inserted_filter

    test_filter.delete(inserted_filter["_id"])


@pytest.fixture()
def multiple_favourite_filters():
    test_filter = FavouriteFilter()
    test_filter.delete_all()

    inserted_filters = test_filter.create_multiple()

    yield inserted_filters

    test_filter.delete_all()


class FavouriteFilter:
    def __init__(self) -> None:
        mongo_client = MongoClient(Config.config.mongodb.mongodb_url)
        og_db = mongo_client[Config.config.mongodb.database_name]
        self.users = og_db["users"]

        self.test_filters = [
            {
                "_id": ObjectId(),
                "name": "Test Filter #1",
                "filter": "PM-201-HJ-CRY-T > PM-201-HJ-CRY-FLOW",
            },
            {
                "_id": ObjectId(),
                "name": "Test Filter #2",
                "filter": "PM-201-HJ-CRY-T < 5",
            },
        ]

    def count(self):
        count_result = self.users.aggregate([{"$match": {"_id": "backend"}}, {"$project": {"count": {"$size": "$filters"}}}])
        for c in count_result:
            return c["count"]

    def find_one(self, filter_id):
        result = self.users.find_one(
            {"_id": "backend"},
            projection={"filters": {"$elemMatch": {"_id": ObjectId(filter_id)}}},
        )
        print(f"Result: {result}")

        if not result:
            return None
        
        result["_id"] = str(result["_id"])
        return result

    def create_one(self):
        filter = self.test_filters[0]
        self.users.update_one({"_id": "backend"}, {"$push": {"filters": filter}})

        

        result = self.users.find_one(
            {"_id": "backend"},
            projection={"filters": {"$elemMatch": {"name": self.test_filters[0]["name"]}}},
        )
        print(f"Result: {result}")

        filter["_id"] = str(filter["_id"])

        return filter

    def create_multiple(self):
        filters = self.test_filters
        self.users.update_one({"_id": "backend"}, {"$push": {"filters": {"$each": filters}}})

        for filter in filters:
            filter["_id"] = str(filter["_id"])

        return filters

    def delete(self, filter_id):
        if self.find_one(filter_id):
            self.users.update_one({"_id": "backend"}, {"$pull": {"filters": {"_id": ObjectId(filter_id)}}})

    def delete_all(self):
        self.users.update_one({"_id": "backend"}, {"$set": {"filters": []}})
