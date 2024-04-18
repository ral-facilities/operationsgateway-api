import logging
from multiprocessing.pool import ThreadPool

from fastapi import APIRouter, Depends, status, UploadFile
from fastapi.responses import JSONResponse
from typing_extensions import Annotated

from operationsgateway_api.src.auth.authorisation import authorise_route
from operationsgateway_api.src.channels.channel_manifest import ChannelManifest
from operationsgateway_api.src.config import Config
from operationsgateway_api.src.error_handling import endpoint_error_handling
from operationsgateway_api.src.records.image import Image
from operationsgateway_api.src.records.ingestion.channel_checks import ChannelChecks
from operationsgateway_api.src.records.ingestion.file_checks import FileChecks
from operationsgateway_api.src.records.ingestion.hdf_handler import HDFDataHandler
from operationsgateway_api.src.records.ingestion.partial_import_checks import (
    PartialImportChecks,
)
from operationsgateway_api.src.records.ingestion.record_checks import RecordChecks
from operationsgateway_api.src.records.record import Record
from operationsgateway_api.src.records.waveform import Waveform


log = logging.getLogger()
router = APIRouter()
AuthoriseRoute = Annotated[str, Depends(authorise_route)]


# TODO - add docstring and move it out of this file
# Looks like where channels have been rejected, it removes them from the variables
# storing the data so they don't get ingested
def _update_data(checker_response, record_data, images, waveforms):
    for key in checker_response["rejected_channels"].keys():
        try:
            channel = record_data.channels[key]
        except KeyError:
            continue

        if channel.metadata.channel_dtype == "image":
            channel_image_path = channel.image_path
            for image in images:
                if image.path == channel_image_path:
                    images.remove(image)
            del record_data.channels[key]

        elif channel.metadata.channel_dtype == "waveform":
            channel_waveform_path = channel.waveform_path
            for waveform in waveforms:
                if waveform.path == channel_waveform_path:
                    waveforms.remove(waveform)
            del record_data.channels[key]

        else:
            del record_data.channels[key]
    return record_data, images, waveforms


@router.post(
    "/submit/hdf",
    summary="Submit a HDF file for ingestion into MongoDB",
    response_description="ID of the record document that has been inserted/updated",
    tags=["Ingestion"],
)
@endpoint_error_handling
async def submit_hdf(
    file: UploadFile,
    access_token: AuthoriseRoute,
):
    """
    This endpoint accepts a HDF file, processes it and stores the data in MongoDB (with
    images being stored on disk). The HDF file should follow the format specified for
    the OperationsGateway project. Example files can be obtained via
    https://github.com/CentralLaserFacility/OG-HDF5, when you provide this tool with
    exported ecat data
    """

    log.info("Submitting CLF data in HDF file to be processed then stored in MongoDB")
    log.debug("Filename: %s, Content: %s", file.filename, file.content_type)

    hdf_handler = HDFDataHandler(file.file)
    (
        record_data,
        waveforms,
        images,
        internal_failed_channel,
    ) = await hdf_handler.extract_data()

    record_original = Record(record_data)
    stored_record = await record_original.find_existing_record()

    accept_type = None
    if stored_record:
        partial_import_checker = PartialImportChecks(
            record_data,
            stored_record,
        )
        accept_type = partial_import_checker.metadata_checks()
        partial_channel_dict = partial_import_checker.channel_checks()

    file_checker = FileChecks(record_data)
    warning = file_checker.epac_data_version_checks()

    record_checker = RecordChecks(record_data)
    record_checker.active_area_checks()
    record_checker.optional_metadata_checks()

    # TODO - ChannelChecks seem to be ran twice somewhere (one in extraction), once
    # further along in the process. Is this true, does this have to be the case?
    channel_checker = ChannelChecks(
        record_data,
        waveforms,
        images,
        internal_failed_channel,
    )
    manifest = await ChannelManifest.get_most_recent_manifest()
    channel_checker.set_channels(manifest)
    channel_dict = await channel_checker.channel_checks()

    # TODO - what's going on here? Can this be added to _update_data()?
    if stored_record:
        log.info("existent record found")
        for key in channel_dict["rejected_channels"].keys():
            if key in partial_channel_dict["accepted_channels"]:
                partial_channel_dict["accepted_channels"].remove(key)
                partial_channel_dict["rejected_channels"][key] = channel_dict[
                    "rejected_channels"
                ][key]
            else:
                partial_channel_dict["rejected_channels"][key] = channel_dict[
                    "rejected_channels"
                ][key]
        checker_response = partial_channel_dict
    else:
        checker_response = channel_dict

    checker_response["warnings"] = list(warning) if warning else []

    record_data, images, waveforms = _update_data(
        checker_response,
        record_data,
        images,
        waveforms,
    )

    record = Record(record_data)

    log.debug("Processing waveforms")
    for w in waveforms:
        waveform = Waveform(w)
        waveform.insert_waveform()
        waveform.create_thumbnail()
        record.store_thumbnail(waveform)

    log.debug("Processing images")
    image_instances = [Image(i) for i in images]
    for image in image_instances:
        image.create_thumbnail()
        record.store_thumbnail(image)

    if len(image_instances) > 0:
        pool = ThreadPool(processes=Config.config.images.upload_image_threads)
        pool.map(Image.upload_image, image_instances)

    if stored_record and accept_type == "accept_merge":
        log.debug(
            "Record matching ID %s already exists in the database, updating existing"
            " document",
            record.record.id_,
        )
        await record.update()
        content = {
            "message": f"Updated {stored_record.id_}",
            "response": checker_response,
        }
        return content
    else:
        log.debug("Inserting new record into MongoDB")
        await record.insert()
        content = {
            "message": f"Added as {record.record.id_}",
            "response": checker_response,
        }
        return JSONResponse(
            content,
            status_code=status.HTTP_201_CREATED,
            headers={"Location": f"/records/{record.record.id_}"},
        )


@router.post(
    "/submit/manifest",
    summary="Submit a channel manifest file for ingestion into MongoDB",
    response_description="ID of the channel metadata document inserted/updated into DB",
    tags=["Ingestion"],
)
@endpoint_error_handling
async def submit_manifest(
    file: UploadFile,
    access_token: AuthoriseRoute,
    bypass_channel_check: bool = False,
):
    log.info("Submitting channel manifest file into database")
    log.debug("Filename: %s, Content: %s", file.filename, file.content_type)

    channel_manifest = ChannelManifest(file.file)
    await channel_manifest.validate(bypass_channel_check)

    await channel_manifest.insert()
    return JSONResponse(
        channel_manifest.data.id_,
        status_code=status.HTTP_201_CREATED,
    )
