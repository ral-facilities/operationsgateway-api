import json
import logging
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, Query

from operationsgateway_api.src.data_encoding import DataEncoding
from operationsgateway_api.src.hdf_handler import HDFDataHandler
from operationsgateway_api.src.helpers import (
    extract_order_data,
    filter_conditions,
    truncate_thumbnail_output,
)
from operationsgateway_api.src.models import Record
from operationsgateway_api.src.mongo.interface import MongoDBInterface

log = logging.getLogger()
router = APIRouter()


@router.get("/records", response_description="Get records using MongoDB's find()")
async def get_records(
    # TODO - investigate linting errors
    conditions: dict = Depends(filter_conditions),  # noqa: B008
    skip: int = 0,
    limit: int = 0,
    order: Optional[List[str]] = Query(None),  # noqa: B008
    projection: Optional[List[str]] = Query(None),  # noqa: B008
    truncate: Optional[bool] = False,
):
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


@router.get("/records/{id_}", response_description="Get record by ID")
# TODO - can I find a use case for conditions?
async def get_record_by_id(
    id_: str,
    conditions: dict = Depends(filter_conditions),  # noqa: B008
    truncate: Optional[bool] = False,
):  # noqa: B008
    log.info("Getting record by ID: %s", id_)

    # TODO - dependent on _id format we decide upon, this may need to be modified
    # TODO - add 404 to this endpoint
    log.debug("test: %s", {"_id": DataEncoding.encode_object_id(id_), **conditions})
    record = await MongoDBInterface.find_one(
        "records",
        {"_id": DataEncoding.encode_object_id(id_), **conditions},
    )

    if truncate:
        truncate_thumbnail_output(record)

    return Record.construct(record.keys(), **record)

# TODO - add /records/count
