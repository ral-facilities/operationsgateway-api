import logging

from fastapi import APIRouter, status, UploadFile
from fastapi.responses import JSONResponse

from operationsgateway_api.src.records.hdf_handler import HDFDataHandler
from operationsgateway_api.src.mongo.interface import MongoDBInterface
from operationsgateway_api.src.records.image import Image
from operationsgateway_api.src.records.ingestion_validator import IngestionValidator
from operationsgateway_api.src.records.record import Record
from operationsgateway_api.src.records.waveform import Waveform


log = logging.getLogger()
router = APIRouter()


@router.post(
    "/submit_hdf",
    summary="Submit a HDF file for ingestion into MongoDB",
    response_description="ID of the record document that has been inserted/updated",
    tags=["Ingestion"],
)
async def submit_hdf(file: UploadFile):
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

    # TODO - move ingestion validation/check whether to reject the file here?

    # TODO - might need some logging?
    for w in waveforms:
        waveform = Waveform(w)
        await waveform.insert_waveform()
        waveform.create_thumbnail()
        record.store_thumbnail(waveform)

    for i in images:
        image = Image(i)
        image.store()
        image.create_thumbnail()
        record.store_thumbnail(image)

    stored_record = await record.find_existing_record()
    ingest_checker = IngestionValidator(record_data, stored_record)

    if stored_record:
        await record.update()
        return f"Updated {stored_record.id_}"
    else:
        await record.insert()
        return JSONResponse(
            record.record.id_,
            status_code=status.HTTP_201_CREATED,
            headers={"Location": f"/records/{record.record.id_}"},
        )

    """
    # TODO - test, it might be broken
    if ingest_checker.stored_record:
        # Cycle through data and detect repeating data
        # Any remaining data should be put into MongoDB via update_one()
        # TODO - needs uncommenting once the class is fixed
        remaining_request_data = record
        '''
        remaining_request_data = IngestionValidator.search_existing_data(
            record_data,
            stored_record,
        )
        '''
        log.debug("Remaining data: %s", remaining_request_data.keys())
        if remaining_request_data:
            return f"Updated {str(stored_record['_id'])}"
        else:
            return f"{str(stored_record['_id'])} not updated, no new data"
    """
