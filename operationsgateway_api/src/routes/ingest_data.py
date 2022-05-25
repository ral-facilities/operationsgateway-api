import logging

from fastapi import APIRouter, UploadFile

from operationsgateway_api.src.data_encoding import DataEncoding
from operationsgateway_api.src.hdf_handler import HDFDataHandler
from operationsgateway_api.src.helpers import (
    insert_waveforms,
    is_shot_stored,
)
from operationsgateway_api.src.mongo.interface import MongoDBInterface


log = logging.getLogger()
router = APIRouter()


@router.post("/submit_hdf", response_description="")
async def submit_hdf(file: UploadFile):
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


@router.post(
    "/submit_hdf/basic",
    response_description="Upload a HDF file, extract the contents and store the data in"
    " MongoDB",
)
async def submit_hdf_basic(file: UploadFile):
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
