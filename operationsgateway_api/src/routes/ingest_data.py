import ctypes
import logging
from multiprocessing.pool import ThreadPool

from fastapi import APIRouter, Depends, status, UploadFile
from fastapi.responses import JSONResponse
from typing_extensions import Annotated

from operationsgateway_api.src.auth.authorisation import authorise_route
from operationsgateway_api.src.channels.channel_manifest import ChannelManifest
from operationsgateway_api.src.config import Config
from operationsgateway_api.src.error_handling import endpoint_error_handling
from operationsgateway_api.src.records.float_image import FloatImage
from operationsgateway_api.src.records.image import Image
from operationsgateway_api.src.records.ingestion.channel_checks import ChannelChecks
from operationsgateway_api.src.records.ingestion.file_checks import FileChecks
from operationsgateway_api.src.records.ingestion.hdf_handler import HDFDataHandler
from operationsgateway_api.src.records.ingestion.partial_import_checks import (
    PartialImportChecks,
)
from operationsgateway_api.src.records.ingestion.record_checks import RecordChecks
from operationsgateway_api.src.records.record import Record
from operationsgateway_api.src.records.vector import Vector
from operationsgateway_api.src.records.waveform import Waveform


log = logging.getLogger()
router = APIRouter()
AuthoriseRoute = Annotated[str, Depends(authorise_route)]


def _update_checker_response(
    checker_response: dict[str, list[str] | dict[str, list[str]]],
    channel: str,
) -> None:
    if channel in checker_response["accepted_channels"]:
        # Remove from accepted_channels and add to rejected_channels
        checker_response["accepted_channels"].remove(channel)
        checker_response["rejected_channels"][channel] = []

    # Append the failure reason to the existing reasons
    checker_response["rejected_channels"][channel].append("Upload to Echo failed")


def _insert(
    entity: Waveform | Vector,
    failed_uploads: list[str],
    record: Record,
) -> None:
    failed_upload = entity.insert()  # Returns channel name if failed
    if failed_upload:
        # if the upload to echo fails, don't process the any further
        return failed_uploads.append(failed_upload)

    entity.create_thumbnail()
    record.store_thumbnail(entity)  # in the record not echo


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
        float_images,
        vectors,
        internal_failed_channel,
    ) = await hdf_handler.extract_data()

    record_original = Record(record_data)
    stored_record = await record_original.find_existing_record()

    file_checker = FileChecks(record_data)
    warning = file_checker.epac_data_version_checks()
    record_checker = RecordChecks(record_data)
    record_checker.active_area_checks()
    record_checker.optional_metadata_checks()

    channel_checker = ChannelChecks(
        ingested_record=record_data,
        ingested_waveforms=waveforms,
        ingested_images=images,
        ingested_float_images=float_images,
        ingested_vectors=vectors,
        internal_failed_channels=internal_failed_channel,
    )
    manifest = await ChannelManifest.get_most_recent_manifest()
    channel_checker.set_channels(manifest)
    channel_dict = await channel_checker.channel_checks()

    if stored_record:
        partial_import_checker = PartialImportChecks(record_data, stored_record)
        accept_type = partial_import_checker.metadata_checks()
        checker_response = partial_import_checker.channel_checks(channel_dict)
    else:
        checker_response = channel_dict

    checker_response["warnings"] = list(warning) if warning else []

    record_data, images, float_images, waveforms, vectors = HDFDataHandler._update_data(
        checker_response,
        record_data,
        images,
        float_images,
        waveforms,
        vectors=vectors,
    )

    record = Record(record_data)

    log.debug("Processing waveforms")
    failed_waveform_uploads = []
    for w in waveforms:
        _insert(Waveform(w), failed_waveform_uploads, record)

    # This section distributes the Image.upload_image calls across
    # the threads in the pool.It takes the image_instances list,
    # applies the Image.upload_image function to each item, and collects
    # the return values in upload_results. The map function blocks the main
    # thread until all the tasks in the pool are complete.
    log.debug("Processing images")
    failed_image_uploads = []
    image_instances = [Image(i) for i in images]
    for image in image_instances:
        image.create_thumbnail()
        record.store_thumbnail(image)  # in the record not echo
    if len(image_instances) > 0:
        pool = ThreadPool(processes=Config.config.images.upload_image_threads)
        upload_results = pool.map(Image.upload_image, image_instances)
        # Filter out successful uploads, collect only failed ones
        failed_image_uploads = [channel for channel in upload_results if channel]
        pool.close()
        image_instances = None

    log.debug("Processing float images")
    failed_float_image_uploads = []
    float_image_instances = [FloatImage(i) for i in float_images]
    for float_image in float_image_instances:
        float_image.create_thumbnail()
        record.store_thumbnail(float_image)  # in the record not echo
    if len(float_image_instances) > 0:
        pool = ThreadPool(processes=Config.config.float_images.upload_image_threads)
        upload_results = pool.map(FloatImage.upload_image, float_image_instances)
        # Filter out successful uploads, collect only failed ones
        failed_float_image_uploads = [channel for channel in upload_results if channel]
        pool.close()
        float_image_instances = None

    log.debug("Processing vectors")
    failed_vector_uploads = []
    for vector_model in vectors:
        _insert(Vector(vector_model), failed_vector_uploads, record)

    # Combine failed channels from waveforms and images and remove them from the record
    # Update the channel checker to reflect failed uploads
    all_failed_upload_channels = (
        failed_waveform_uploads
        + failed_image_uploads
        + failed_float_image_uploads
        + failed_vector_uploads
    )
    for channel in all_failed_upload_channels:
        record.remove_channel(channel)
        _update_checker_response(checker_response, channel)

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
        ctypes.CDLL("libc.so.6").malloc_trim(0)
        return content
    else:
        log.debug("Inserting new record into MongoDB")
        await record.insert()
        record_id = record.record.id_
        content = {
            "message": f"Added as {record_id}",
            "response": checker_response,
        }

        # Emptying variables to save memory
        images = []
        float_images = []
        hdf_handler.images = []
        hdf_handler.float_images = []
        hdf_handler.vectors = []
        hdf_handler = None
        channel_checker = None
        waveforms = None
        ctypes.CDLL("libc.so.6").malloc_trim(0)
        return JSONResponse(
            content,
            status_code=status.HTTP_201_CREATED,
            headers={"Location": f"/records/{record_id}"},
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
