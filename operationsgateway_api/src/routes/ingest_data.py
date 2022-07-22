import logging

from fastapi import APIRouter, UploadFile

from operationsgateway_api.src.data_encoding import DataEncoding
from operationsgateway_api.src.hdf_handler import HDFDataHandler
from operationsgateway_api.src.helpers import (
    create_image_thumbnails,
    create_waveform_thumbnails,
    insert_waveforms,
    is_shot_stored,
    store_image_thumbnails,
    store_images,
    store_waveform_thumbnails,
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
    store_images(images)

    # Create and store thumbnails from stored images
    image_thumbnails = create_image_thumbnails(images.keys())
    store_image_thumbnails(record, image_thumbnails)

    waveform_thumbnails = create_waveform_thumbnails(waveforms)
    store_waveform_thumbnails(record, waveform_thumbnails)

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
            # This update query has been split into two one (which is iterated in a
            # loop) to add record metadata, and another to add each of the channels.
            # Based on some quick dev testing while making sure it worked, this doesn't
            # slow down ingestion times
            for metadata_key, value in remaining_request_data["metadata"].items():
                await MongoDBInterface.update_one(
                    "records",
                    {"_id": remaining_request_data["_id"]},
                    {"$set": {f"metadata.{metadata_key}": value}},
                )

            await MongoDBInterface.update_one(
                "records",
                {"_id": remaining_request_data["_id"]},
                {
                    "$addToSet": {
                        "channels": {"$each": remaining_request_data["channels"]},
                    },
                },
            )

            return f"Updated {str(shot_document['_id'])}"
        else:
            return f"{str(shot_document['_id'])} not updated, no new data"
    else:
        data_insert = await MongoDBInterface.insert_one("records", record)
        return MongoDBInterface.get_inserted_id(data_insert)
