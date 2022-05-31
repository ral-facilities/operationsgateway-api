import logging

from fastapi import APIRouter, UploadFile

from operationsgateway_api.src.data_encoding import DataEncoding
from operationsgateway_api.src.hdf_handler import HDFDataHandler
from operationsgateway_api.src.helpers import (
    create_thumbnails,
    insert_waveforms,
    is_shot_stored,
    store_images,
    store_thumbnails,
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

    record, waveforms, images = HDFDataHandler.extract_hdf_data(hdf_file=hdf_file)
    DataEncoding.encode_numpy_for_mongo(record)

    file_shot_num = record["metadata"]["shotnum"]

    # Always insert images and waveforms for now
    await insert_waveforms(waveforms)
    await store_images(images)

    # Create and store thumbnails from stored images
    thumbnails = create_thumbnails(images.keys())
    store_thumbnails(record, thumbnails)

    shot_document = await MongoDBInterface.find_one(
        "records",
        filter_={"metadata.shotnum": file_shot_num},
    )
    shot_exist = is_shot_stored(shot_document)

    if shot_exist:
        # When an existing shot is stored, overwrite the newly generated ID with the one
        # that already exists in the database
        record["_id"] = shot_document["_id"]

        # Cycle through data and detect repeating data
        # Any remaining data should be put into MongoDB via update_one()
        remaining_request_data = HDFDataHandler.search_existing_data(
            record,
            shot_document,
        )
        log.debug("Remaining data: %s", remaining_request_data.keys())
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
        data_insert = await MongoDBInterface.insert_one("records", record)
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

    # TODO - do something with these images
    record, waveforms, images = HDFDataHandler.extract_hdf_data(hdf_file=hdf_file)
    DataEncoding.encode_numpy_for_mongo(record)

    await insert_waveforms(waveforms)
    await store_images(images)
    record_insert = await MongoDBInterface.insert_one("records", record)

    return MongoDBInterface.get_inserted_id(record_insert)
