import json
import logging
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, Query, UploadFile

from operationsgateway_api.src.data_encoding import DataEncoding
from operationsgateway_api.src.hdf_handler import HDFDataHandler
from operationsgateway_api.src.helpers import (
    extract_order_data,
    filter_conditions,
    insert_waveforms,
    is_shot_stored,
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


@router.post(
    "/submit_hdf/basic",
    response_description="Upload a HDF file, extract the contents and store the data in"
    " MongoDB",
)
async def upload_file(file: UploadFile):
    log.info("Adding contents of attached file to MongoDB")
    log.debug("Filename: %s, Content: %s", file.filename, file.content_type)

    file_contents = await file.read()
    hdf_file = HDFDataHandler.convert_to_hdf_from_request(file_contents)

    record, waveforms = HDFDataHandler.extract_hdf_data(hdf_file=hdf_file)
    DataEncoding.encode_numpy_for_mongo(record)

    # TODO - call the function instead
    if waveforms:
        for waveform in waveforms:
            DataEncoding.encode_numpy_for_mongo(waveform)

        log.debug("Waveforms: %s, Length: %s", waveforms, len(waveforms))
        await MongoDBInterface.insert_many("waveforms", waveforms)

    record_insert = await MongoDBInterface.insert_one("records", record)

    return MongoDBInterface.get_inserted_id(record_insert)


@router.post("/submit_hdf", response_description="")
async def submit_hdf(file: UploadFile):
    # Convert from request format to HDF via h5py
    # Extract data from the file to put it into a dictionary, encode it afterwards
    # Query the database to see if the shot already exists
    # If shot exists:
    # Go through the h5 file and see if any data that already exists is present again in the new file
    # This would require fetching the entire document and iterating through it
    # If data appears again:
    # Leave a mechanism open for this to be implemented later on
    # Not sure what we should do, but we could either:
    # Return an error to the client (400, with error message?)
    # Ignore the new data (i.e. take it out of the extracted data so it doesn't go into MongoDB)
    # Blindly overwrite the data (so a check wouldn't be needed effectively)
    # Append this h5 file to existing document
    # Else if shot doesn't exist:
    # Create a new document to store data

    log.info("Submitting CLF data in HDF file to be processed then stored in MongoDB")
    log.debug("Filename: %s, Content: %s", file.filename, file.content_type)

    file_contents = await file.read()
    hdf_file = HDFDataHandler.convert_to_hdf_from_request(file_contents)

    records, waveforms = HDFDataHandler.extract_hdf_data(hdf_file=hdf_file)
    DataEncoding.encode_numpy_for_mongo(records)

    file_shot_num = records["metadata"]["shotnum"]

    shot_document = await MongoDBInterface.find_one(
        "records",
        filter_={"metadata.shotnum": file_shot_num},
    )

    shot_exist = is_shot_stored(shot_document)

    if shot_exist:
        # Cycle through data and detect repeating data
        # Any remaining data should be put into MongoDB via update_one()
        remaining_request_data = HDFDataHandler.search_existing_data(
            records,
            shot_document,
        )
        await insert_waveforms(waveforms)
        log.debug("Remaining data: %s", remaining_request_data)
        if remaining_request_data:
            await MongoDBInterface.update_one(
                "records",
                {"metadata.shotnum": file_shot_num},
                {"$set": remaining_request_data},
            )
            return f"Updated {str(shot_document['_id'])}"
        else:
            return f"{str(shot_document['_id'])} not updated, no new data"
    else:
        await insert_waveforms(waveforms)
        data_insert = await MongoDBInterface.insert_one("records", records)
        return MongoDBInterface.get_inserted_id(data_insert)
