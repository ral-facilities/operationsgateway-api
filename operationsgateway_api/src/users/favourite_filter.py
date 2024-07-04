from enum import Enum
import logging
from typing import List, Optional

from bson import ObjectId
from bson.errors import InvalidId
from pydantic import ValidationError
from pymongo.results import UpdateResult

from operationsgateway_api.src.exceptions import (
    DatabaseError,
    MissingDocumentError,
    ModelError,
    UserError,
)
from operationsgateway_api.src.models import FavouriteFilterModel
from operationsgateway_api.src.mongo.interface import MongoDBInterface

log = logging.getLogger()


class FilterCRUDOperation(Enum):
    """
    Enum used to pass `_process_update_result()`, used as a signal to know whether the
    results being processed are a result of an update or a delete. As the favourite
    filters are embedded into a document in the users collection, deleting a favourite
    filter requires using the `update_one()` operation to MongoDB, so we can't discern
    the difference based on what operation is sent to the database, hence the need for
    this enum
    """

    DELETE = 1
    UPDATE = 2


class FavouriteFilter:
    def __init__(
        self,
        username: str,
        name: str,
        filter_: str,
        id_: Optional[str] = None,
    ) -> None:
        if name == "":
            raise UserError("Name of filter cannot be empty")
        if filter_ == "":
            raise UserError("Filter cannot be empty")

        try:
            self.filter_id = ObjectId(id_) if id_ else ObjectId()
        except InvalidId as exc:
            raise UserError(f"Invalid Object ID entered: {id_}") from exc
        self.filter = {"_id": self.filter_id, "name": name, "filter": filter_}
        self.username = username

    @staticmethod
    async def get_list(username: str) -> List[FavouriteFilterModel]:
        """
        Get a list of favourite filters for a particular user, convert the list of
        dictionaries to a list of `FavouriteFilterModel` to ensure the filters are
        formatted correctly
        """

        log.info("Finding all favourite filters belonging to user '%s'", username)
        results = await MongoDBInterface.find_one(
            "users",
            filter_={"_id": username},
            projection=["filters"],
        )
        filters = results.get("filters", [])
        log.debug(
            "Number of favourite filters found for user '%s': %d",
            username,
            len(filters),
        )

        try:
            filter_list = [FavouriteFilterModel(**result) for result in filters]
        except ValidationError as exc:
            raise ModelError(str(exc)) from exc

        return filter_list

    @staticmethod
    async def get_by_id(username: str, id_: str) -> FavouriteFilterModel:
        """
        Return a specific favourite filter (as a `FavouriteFilterModel`), given its ID
        and the user it belongs to. As filters are embedded within a user document,
        both the filter ID and username of who it belongs to must be passed to this
        method

        $elemMatch is used to query the database and iterate through the list of
        filters, returning only the one that where the _id matches. This is a more
        efficient alternative to getting all the filters from the query and searching
        for the correct one within this function
        """

        log.info("Finding favourite filter '%s' for user '%s'", username, id_)
        try:
            results = await MongoDBInterface.find_one(
                "users",
                filter_={"_id": username},
                projection={"filters": {"$elemMatch": {"_id": ObjectId(id_)}}},
            )
        except InvalidId as exc:
            raise ModelError("ID provided is not a valid ObjectId") from exc
        filter_ = results["filters"][0]

        try:
            return FavouriteFilterModel(**filter_)
        except ValidationError as exc:
            raise ModelError(str(exc)) from exc

    @staticmethod
    async def delete(username: str, id_: str) -> None:
        """
        Delete a favourite filter from a user's document. As the filters are embedded
        into a user document, the filter must be deleted using `update_one()` rather
        than `delete_one()`
        """

        try:
            log.info("Deleting favourite filter '%s' for user '%s'", id_, username)
            update_result = await MongoDBInterface.update_one(
                "users",
                {"_id": username},
                {
                    "$pull": {"filters": {"_id": ObjectId(id_)}},
                },
            )
        except InvalidId as exc:
            raise ModelError("ID provided is not a valid ObjectId") from exc

        FavouriteFilter._process_update_result(
            update_result,
            username,
            id_,
            FilterCRUDOperation.DELETE,
        )

    async def create(self) -> ObjectId:
        """
        Store a favourite filter in the database using the instance variables
        """

        log.info(
            "Creating favourite filter called '%s' for user '%s'",
            self.filter["name"],
            self.username,
        )
        log.debug("Favourite filter to be created: %s", self.filter)
        update_result = await MongoDBInterface.update_one(
            "users",
            {"_id": self.username},
            {"$push": {"filters": self.filter}},
        )

        if update_result.matched_count != 1 or update_result.modified_count != 1:
            log.error(
                "Problem creating a favourite filter for user '%s'."
                " Favourite filter: '%s', Update Result from MongoDB: %s",
                self.username,
                self.filter,
                update_result,
            )
            raise DatabaseError(
                f"Favourite filter cannot be created for user '{self.username}'",
            )

        return self.filter_id

    async def update(self) -> None:
        """
        Update a favourite filter in the database using the instance variables
        """

        log.debug("Updated favourite filter submitted: %s", self.filter)
        update_result = await MongoDBInterface.update_one(
            "users",
            {"_id": self.username, "filters._id": self.filter_id},
            {"$set": {"filters.$": self.filter}},
        )

        FavouriteFilter._process_update_result(
            update_result,
            self.username,
            str(self.filter_id),
            FilterCRUDOperation.UPDATE,
        )

    @staticmethod
    def _process_update_result(
        update_result: UpdateResult,
        username: str,
        id_: str,
        operation: FilterCRUDOperation,
    ) -> None:
        """
        Use an instance of `UpdateResult` and catch any errors from an unexpected
        database update operation
        """

        if update_result.matched_count != 1:
            log.error(
                "Error (matched count != 1) when performing %s operation on favourite"
                " filter '%s' for user '%s'. Update Result from MongoDB: %s",
                operation.name.lower(),
                id_,
                username,
                update_result,
            )
            raise MissingDocumentError(
                f"Favourite filter cannot be found for user '{username}'",
            )
        if update_result.modified_count != 1:
            log.error(
                "Error (modified count != 1) when performing %s operation on favourite"
                " filter '%s' for user '%s'. Update Result from MongoDB: %s",
                operation.name.lower(),
                id_,
                username,
                update_result,
            )
            raise DatabaseError(
                f"Change to favourite filter {id_} has been unsuccessful",
            )
