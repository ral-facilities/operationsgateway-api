import logging
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple, Union

from pymongo.collection import Collection
from pymongo.cursor import Cursor
from pymongo.errors import DuplicateKeyError, InvalidName, PyMongoError, WriteError
from pymongo.results import (
    DeleteResult,
    InsertManyResult,
    InsertOneResult,
    UpdateResult,
)

from operationsgateway_api.src.config import Config
from operationsgateway_api.src.exceptions import DatabaseError, DuplicateSessionError
from operationsgateway_api.src.mongo.connection import get_mongodb_connection
from operationsgateway_api.src.mongo.mongo_error_handling import mongodb_error_handling

log = logging.getLogger()
ProjectionAlias = Optional[Union[Mapping[str, Any], Iterable[str]]]


class MongoDBInterface:
    """
    An implementation of various PyMongo and Motor functions that suit our specific
    database and collection names

    Motor doesn't support type annotations (see
    https://jira.mongodb.org/browse/MOTOR-331 for any updates) so type annotations are
    used from PyMongo which from a user perspective, acts almost identically (excluding
    async support of course). This means the type hinting can actually be useful for
    developers of this repo
    """

    @staticmethod
    @mongodb_error_handling("get_collection_object")
    def get_collection_object(collection_name: str) -> Collection:
        """
        Simple getter function which gets a particular collection so it can be
        manipulated (in a function within this class) to perform a CRUD operation
        """
        try:
            return get_mongodb_connection().db[collection_name]
        except InvalidName as exc:
            log.error("Invalid collection name given: %s", collection_name)
            raise DatabaseError("Invalid collection name given") from exc

    @staticmethod
    @mongodb_error_handling("find")
    def find(
        collection_name: str = "images",
        filter_: dict = None,
        skip: int = 0,
        limit: int = 0,
        sort: Union[str, List[Tuple[str, int]]] = "",
        projection: ProjectionAlias = None,
    ) -> Cursor:
        """
        Creates a query to find documents in a given collection, based on filters
        provided

        Due to Motor being asynchronous, the query is executed in `query_to_list()`, not
        in this function
        """

        if filter_ is None:
            filter_ = {}

        log.info("Sending find() to MongoDB, collection: %s", collection_name)
        log.debug(
            "Filter: %s, Skip: %d, Limit: %s, Order: %s, Projection: %s",
            filter_,
            skip,
            limit,
            sort,
            projection,
        )

        collection = MongoDBInterface.get_collection_object(collection_name)
        return collection.find(
            filter=filter_,
            skip=skip,
            limit=limit,
            sort=sort,
            projection=projection,
        )

    @staticmethod
    @mongodb_error_handling("query_to_list")
    async def query_to_list(query: Cursor) -> List[Dict[str, Any]]:
        """
        Sends the query to MongoDB and converts the query results into a list

        The configured maximum number of documents effectively limits the result set,
        but this value is expected to be several hundred/thousand
        """

        log.info(
            "Getting query results and converting them into a list: %d",
            Config.config.mongodb.max_documents,
        )

        return await query.to_list(length=Config.config.mongodb.max_documents)

    @staticmethod
    @mongodb_error_handling("find_one")
    async def find_one(
        collection_name: str,
        filter_: Dict[str, Any] = None,
        sort: List[Tuple[str, int]] = None,
        projection: ProjectionAlias = None,
    ) -> Dict[str, Any]:
        """
        Based on a filter, find a single document in the record collection of MongoDB
        """

        if filter_ is None:
            filter_ = {}

        log.info("Sending find_one() to MongoDB, collection: %s", collection_name)
        log.debug("Filter: %s, Sort: %s, Projection: %s", filter_, sort, projection)

        collection = MongoDBInterface.get_collection_object(collection_name)

        return await collection.find_one(filter_, sort=sort, projection=projection)

    @staticmethod
    @mongodb_error_handling("update_one")
    async def update_one(
        collection_name: str,
        filter_: Dict[str, Any] = None,
        update: Dict[str, Any] = None,
        upsert: bool = False,
    ) -> UpdateResult:
        """
        Update a single document using the data provided. The document selected for the
        update is based on the input of the query filter
        """

        if filter_ is None:
            filter_ = {}
        if update is None:
            update = {}

        log.info("Sending update_one() to MongoDB, collection: %s", collection_name)
        log.debug("Filter: %s", filter_)

        collection = MongoDBInterface.get_collection_object(collection_name)
        try:
            return await collection.update_one(
                filter_,
                update,
                upsert=upsert,
            )
        except WriteError as exc:
            log.exception(msg=exc)
            raise DatabaseError(
                f"Error when updating single document in {collection_name} collection",
            ) from exc

    @staticmethod
    @mongodb_error_handling("update_many")
    async def update_many(
        collection_name: str,
        filter_: Dict[str, Any] = {},  # noqa: B006
        update: Dict[str, Any] = {},  # noqa: B006
        upsert: bool = False,
    ):
        log.info("Sending update_many() to MongoDB, collection: %s", collection_name)
        log.debug("Filter: %s", filter_)

        collection = MongoDBInterface.get_collection_object(collection_name)

        try:
            return await collection.update_many(
                filter_,
                update,
                upsert=upsert,
            )
        except WriteError as exc:
            raise DatabaseError(
                "Error when updating multiple documents in %s collection",
                collection_name,
            ) from exc

    @staticmethod
    @mongodb_error_handling("insert_one")
    async def insert_one(collection_name: str, data: Dict[str, Any]) -> InsertOneResult:
        """
        Using the input data, insert a single document into a given collection
        """

        log.info("Sending insert_one() to MongoDB, collection: %s", collection_name)

        collection = MongoDBInterface.get_collection_object(collection_name)
        try:
            return await collection.insert_one(data)
        except DuplicateKeyError as exc:
            log.exception(msg=exc)
            raise DuplicateSessionError(
                "Session name already exists for this user.",
            ) from exc
        except WriteError as exc:
            log.exception(msg=exc)
            raise DatabaseError(
                f"Error when inserting single document in {collection_name} collection",
            ) from exc

    @staticmethod
    @mongodb_error_handling("insert_many")
    async def insert_many(
        collection_name: str,
        data: List[Dict[str, Any]],
    ) -> InsertManyResult:
        """
        Using the input data, insert multiple documents into a given collection
        """

        log.info("Sending insert_many() to MongoDB, collection: %s", collection_name)

        collection = MongoDBInterface.get_collection_object(collection_name)
        try:
            return await collection.insert_many(data)
        except WriteError as exc:
            log.exception(msg=exc)
            raise DatabaseError(
                f"Error when inserting multiple documents in {collection_name}"
                " collection",
            ) from exc

    @staticmethod
    @mongodb_error_handling("delete_one")
    async def delete_one(
        collection_name: str,
        filter_: Dict[str, Any] = None,
    ) -> DeleteResult:
        """
        Given a condition, delete a single document from a collection
        """

        if filter_ is None:
            filter_ = {}

        log.info("Sending delete_one() to MongoDB, collection: %s", collection_name)

        collection = MongoDBInterface.get_collection_object(collection_name)
        try:
            return await collection.delete_one(filter_)
        except PyMongoError as exc:
            log.error(
                "Error removing single document in %s collection. The following filter"
                " was used: %s",
                collection_name,
                filter_,
            )
            log.exception(msg=exc)
            raise DatabaseError(
                "Error removing document from MongoDB, collection: %s",
                collection_name,
            ) from exc

    @staticmethod
    @mongodb_error_handling("count_documents")
    async def count_documents(
        collection_name: str,
        filter_: Dict[str, Any] = None,
    ) -> int:
        log.info(
            "Sending count_documents() to MongoDB, collection: %s",
            collection_name,
        )

        if filter_ is None:
            filter_ = {}

        collection = MongoDBInterface.get_collection_object(collection_name)
        try:
            return await collection.count_documents(filter_)
        except PyMongoError as exc:
            log.error(
                "Error counting documents. Collection: %s, filter: %s",
                collection_name,
                filter_,
            )
            log.exception(msg=exc)
            raise DatabaseError(
                "Error counting the number of documents in collection %s",
                collection_name,
            ) from exc

    @staticmethod
    @mongodb_error_handling("aggregate")
    async def aggregate(
        collection_name: str,
        pipeline,
    ):
        collection = MongoDBInterface.get_collection_object(collection_name)
        aggregate_query = collection.aggregate(pipeline)
        return await MongoDBInterface.query_to_list(aggregate_query)
