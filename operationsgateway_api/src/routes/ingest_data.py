import logging
from multiprocessing.pool import ThreadPool

from fastapi import APIRouter, Depends, status, UploadFile
from fastapi.responses import JSONResponse
from typing_extensions import Annotated

from operationsgateway_api.src.auth.authorisation import authorise_route
from operationsgateway_api.src.channels.channel_manifest import ChannelManifest
from operationsgateway_api.src.config import Config
from operationsgateway_api.src.error_handling import endpoint_error_handling
from operationsgateway_api.src.records.hdf_handler import HDFDataHandler
from operationsgateway_api.src.records.image import Image
from operationsgateway_api.src.records.ingestion_validator import IngestionValidator
from operationsgateway_api.src.records.record import Record
from operationsgateway_api.src.records.waveform import Waveform


log = logging.getLogger()
router = APIRouter()
AuthoriseRoute = Annotated[str, Depends(authorise_route)]


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
    record_data, waveforms, images = hdf_handler.extract_data()
    record = Record(record_data)

    stored_record = await record.find_existing_record()
    # TODO - when I implement the validation, it should only run if `stored_record`
    # actually contains something (i.e. isn't None)
    ingest_checker = IngestionValidator(record_data, stored_record)  # noqa: F841

    log.debug("Processing waveforms")
    for w in waveforms:
        waveform = Waveform(w)
        await waveform.insert_waveform()
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

    if stored_record:
        log.debug(
            "Record matching ID %s already exists in the database, updating existing"
            " document",
            record.record.id_,
        )
        await record.update()
        return f"Updated {stored_record.id_}"
    else:
        log.debug("Inserting new record into MongoDB")
        await record.insert()
        return JSONResponse(
            record.record.id_,
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
