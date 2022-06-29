from http import HTTPStatus
import logging
from typing import List, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, Path, Query, Response

from operationsgateway_api.src.data_encoding import DataEncoding
from operationsgateway_api.src.helpers import (
    extract_order_data,
    filter_conditions,
    truncate_thumbnail_output,
)
from operationsgateway_api.src.models import Record
from operationsgateway_api.src.mongo.interface import MongoDBInterface

log = logging.getLogger()
router = APIRouter()


@router.get(
    "/records",
    summary="Get records using database-like filters",
    response_description="List of records",
    tags=["Records"],
)
async def get_records(
    # TODO - investigate linting errors
    conditions: dict = Depends(filter_conditions),  # noqa: B008
    skip: int = Query(
        0,
        description="How many documents should be skipped before returning results",
    ),
    limit: int = Query(
        0, description="How many documents the result should be limited to",
    ),
    order: Optional[List[str]] = Query(
        None,
        description="Specify order of results in the format of `field_name ASC`",
        examples={
            "asc": {
                "summary": "Shot number ascending",
                "value": "metadata.shotnum ASC",
            },
            "desc": {"summary": "ID descending", "value": "_id DESC"},
        },
    ),  # noqa: B008
    projection: Optional[List[str]] = Query(
        None,
        description="Select specific fields in the record e.g. `metadata.shotnum`",
        examples={
            "metadata": {"summary": "Shot number", "value": "metadata.shotnum"},
            "channel_data": {"summary": "Channel data", "value": "channels.data"},
        },
    ),  # noqa: B008
    truncate: Optional[bool] = Query(
        False,
        description="Parameter used for development to reduce the output of thumbnail"
        " strings to 50 characters",
    ),
):
    """
    This endpoint uses MongoDB's find() method to query the records
    collection. As a result, this endpoint exposes some of this functionality, which
    you can find more information about at:
    https://www.mongodb.com/docs/manual/reference/method/db.collection.find
    """

    log.info("Getting records by query")

    query_order = list(extract_order_data(order)) if order else ""

    records_query = MongoDBInterface.find(
        collection_name="records",
        filter_=conditions,
        skip=skip,
        limit=limit,
        sort=query_order,
        projection=projection,
    )
    records = await MongoDBInterface.query_to_list(records_query)

    if truncate:
        for record in records:
            truncate_thumbnail_output(record)

    # TODO - do I need this model stuff?
    return [Record.construct(record.keys(), **record) for record in records]


@router.get(
    "/records/count",
    summary="Count the number of records stored based on given conditions to restrict"
    " the search",
    response_description="Record count",
    tags=["Records"],
)
async def count_records(conditions: dict = Depends(filter_conditions)):  # noqa: B008
    """
    This endpoint uses the `conditions` query parameter (i.e. like a WHERE filter) in
    the same way as GET `/records`. For example, there is a WHERE filter is not
    applicable to a GET by ID request in DataGateway API
    """

    log.info("Counting records using given conditions")
    return await MongoDBInterface.count_documents("records", conditions)


@router.get(
    "/records/{id_}",
    summary="Get a record specified by its ID",
    response_description="Single record object",
    tags=["Records"],
)
# TODO - can I find a use case for conditions?
async def get_record_by_id(
    id_: str = Path(..., description="`_id` of the record to fetch from the database"),
    conditions: dict = Depends(filter_conditions),  # noqa: B008
    truncate: Optional[bool] = Query(
        False,
        description="Parameter used for development to reduce the output of thumbnail"
        " strings to 50 characters",
    ),
):  # noqa: B008
    """
    Get a single record by its ID. The `conditions` query parameter exists but a
    specific use case is uncertain at this stage because the ID is the element that
    tells MongoDB which record to retrieve
    """

    log.info("Getting record by ID: %s", id_)

    # TODO - dependent on _id format we decide upon, this may need to be modified
    # TODO - add 404 to this endpoint
    record = await MongoDBInterface.find_one(
        "records",
        {"_id": DataEncoding.encode_object_id(id_), **conditions},
    )

    if truncate:
        truncate_thumbnail_output(record)

    return Record.construct(record.keys(), **record)


@router.delete(
    "/records/{id_}",
    summary="Delete a record specified by its ID",
    response_description="No content",
    status_code=204,
    tags=["Records"],
)
async def delete_record_by_id(
    id_: str = Path(..., description="`_id` of the record to delete from the database"),
):
    # TODO - full implementation will require searching through waveform channels to
    # remove the documents in the waveforms collection. The images will need to be
    # removed from disk too
    log.info("Deleting record by ID: %s", id_)

    await MongoDBInterface.delete_one("records", {"_id": ObjectId(id_)})

    return Response(status_code=HTTPStatus.NO_CONTENT.value)
