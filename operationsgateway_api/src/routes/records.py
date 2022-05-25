import json
import logging
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, Query

from operationsgateway_api.src.data_encoding import DataEncoding
from operationsgateway_api.src.hdf_handler import HDFDataHandler
from operationsgateway_api.src.helpers import (
    extract_order_data,
    filter_conditions,
)
from operationsgateway_api.src.models import Record
from operationsgateway_api.src.mongo.interface import MongoDBInterface

log = logging.getLogger()
router = APIRouter()

@router.get("/records/find", response_description="Get records using MongoDB's find()")
async def get_records(
    # TODO - investigate linting errors
    conditions: dict = Depends(filter_conditions),  # noqa: B008
    skip: int = 0,
    limit: int = 0,
    order: Optional[List[str]] = Query(None),  # noqa: B008
    projection: Optional[List[str]] = Query(None),  # noqa: B008
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

    # TODO - do I need this model stuff?
    return [Record.construct(record.keys(), **record) for record in records]


@router.get(
    "/records/aggregate", response_description="Get records by MongoDB aggregation",
)
async def get_record_by_aggregation(pipeline: Optional[List[str]] = Query(None)):
    log.debug("Pipeline: %s, Type: %s", pipeline, type(pipeline))
    log.info("Getting records by MongoDB aggregation")

    # TODO - if matching on _id, the ID needs to be encoded to an ObjectId
    records_query = MongoDBInterface.aggregate("records", json.loads(pipeline[0]))
    records = await MongoDBInterface.query_to_list(records_query)

    return [Record.construct(record.keys(), **record) for record in records]


@router.get("/records/{id_}", response_description="Get record by ID")
# TODO - can I find a use case for conditions?
async def get_record_by_id(id_: str, conditions: dict = Depends(filter_conditions)):  # noqa: B008
    log.info("Getting record by ID: %s", id_)

    # TODO - dependent on _id format we decide upon, this may need to be modified
    # TODO - add 404 to this endpoint
    log.debug("test: %s", {"_id": DataEncoding.encode_object_id(id_), **conditions})
    record = await MongoDBInterface.find_one(
        "records",
        {"_id": DataEncoding.encode_object_id(id_), **conditions},
    )
    return Record.construct(record.keys(), **record)


@router.patch(
    "/records/{id_}",
    response_description="Update or add new fields to a record by ID",
)
async def update_record_by_id(id_: str, new_data: dict = Body(...)):  # noqa: B008
    log.info("Updating record by ID: %s", id_)
    log.debug("New Data: %s, Type: %s", new_data, type(new_data))

    # TODO - would find_one_and_update() be better?
    await MongoDBInterface.update_one(
        "records",
        {"_id": DataEncoding.encode_object_id(id_)},
        {"$set": new_data},
    )

    return await get_record_by_id(id_)


@router.post("/records", response_description="Insert hardcoded record")
async def insert_record():
    log.info("Inserting record (currently static/hardcoded file on disk)")

    hdf_data = HDFDataHandler.extract_hdf_data(
        file_path="/root/seg_dev/OG-HDF5/output_data/366375.h5",
    )
    DataEncoding.encode_numpy_for_mongo(hdf_data)
    data_insert = await MongoDBInterface.insert_one("records", hdf_data)

    return MongoDBInterface.get_inserted_id(data_insert)

# TODO - add /records/count