import io
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Response
from pydantic import Json
import pymongo
from typing_extensions import Annotated

from operationsgateway_api.src.auth.authorisation import (
    authorise_token,
)
from operationsgateway_api.src.channels.channel_manifest import ChannelManifest
from operationsgateway_api.src.config import Config
from operationsgateway_api.src.error_handling import endpoint_error_handling
from operationsgateway_api.src.exceptions import ExportError
from operationsgateway_api.src.records.export_handler import ExportHandler
from operationsgateway_api.src.records.record import Record as Record
from operationsgateway_api.src.routes.common_parameters import ParameterHandler


log = logging.getLogger()
router = APIRouter()
AuthoriseToken = Annotated[str, Depends(authorise_token)]
max_filesize_bytes = Config.config.export.max_filesize_bytes


@router.get(
    "/export",
    summary="Export records using database-like filters",
    response_description="File containing exported data. This will be a CSV file if "
    "only scalar values are exported, or a zip file if images "
    "and/or waveforms are included.",
    tags=["Data Export"],
)
@endpoint_error_handling
async def export_records(
    access_token: AuthoriseToken,
    conditions: Json = Query(
        {},
        description="Conditions to apply to the query. Use an _id $in query to export "
        "specific records.",
    ),
    skip: int = Query(
        0,
        description="How many documents should be skipped before returning results",
    ),
    limit: int = Query(
        0,
        description="How many documents the result should be limited to",
    ),
    order: Optional[List[str]] = Query(
        None,
        description="Specify order of results in the format of `field_name ASC`",
    ),
    projection: Optional[List[str]] = Query(
        None,
        description="Select specific fields in the record e.g. `metadata.shotnum`",
    ),
    lower_level: Optional[int] = Query(
        0,
        description="The lower level threshold for false colour (0-255)",
        ge=0,
        le=255,
    ),
    upper_level: Optional[int] = Query(
        255,
        description="The upper level threshold for false colour (0-255)",
        ge=0,
        le=255,
    ),
    colourmap_name: Optional[str] = Query(
        None,
        description="The name of the matplotlib colour map to apply to the image"
        " thumbnails",
    ),
    export_scalars: Optional[bool] = Query(
        True,
        description="Whether to export the scalar values from the main data table",
    ),
    export_images: Optional[bool] = Query(
        True,
        description="Whether to export the images for image channels",
    ),
    export_waveform_csvs: Optional[bool] = Query(
        True,
        description="Whether to export the waveforms in CSV files",
    ),
    export_waveform_images: Optional[bool] = Query(
        False,
        description="Whether to export rendered images of the waveforms",
    ),
):
    """
    Export the specified data to a file for download.
    The request follows the same format as the /records endpoint which returns the data
    primarily for display purposes.
    The data requested can be:
    - the specified columns for all data matching the search query
      (skip and limit might be used to limit the results to just those currently
      displayed)
    - the specified columns for the specified records only
      (to achieve this a "conditions" parameter of the following format can be used:
      {"_id": {"$in": ["20230605080000","20230605090000","20230605100000"]}}
      )
    """

    log.info("Exporting records")

    if projection is None:
        raise ExportError("No channels specified to export")

    query_order = (
        list(ParameterHandler.extract_order_data(order))
        if order
        else [("_id", pymongo.ASCENDING)]
    )
    log.info("conditions: %s", conditions)
    ParameterHandler.encode_date_for_conditions(conditions)

    records_data = await Record.find_record(
        conditions,
        skip,
        limit,
        query_order,
        projection,
    )

    if len(records_data) == 0:
        raise ExportError("No records found to export")

    channel_mainfest_dict = await ChannelManifest.get_most_recent_manifest()

    export_handler = ExportHandler(
        records_data,
        channel_mainfest_dict,
        projection,
        lower_level,
        upper_level,
        colourmap_name,
        export_scalars,
        export_images,
        export_waveform_csvs,
        export_waveform_images,
    )

    await export_handler.process_records()
    file_bytes_to_export = export_handler.get_export_file_bytes()
    # ensure the "file pointer" is reset
    file_bytes_to_export.seek(0)
    filename = export_handler.get_filename_stem()
    if type(file_bytes_to_export) == io.BytesIO:
        # this is a zip file
        headers = {"Content-Disposition": f'attachment; filename="{filename}.zip"'}
        return Response(
            file_bytes_to_export.read(),
            headers=headers,
            media_type="application/zip",
        )
    elif type(file_bytes_to_export) == io.StringIO:
        # this is a csv file
        headers = {"Content-Disposition": f'attachment; filename="{filename}.csv"'}
        return Response(
            file_bytes_to_export.read(),
            headers=headers,
            media_type="text/plain",
        )
    else:
        log.error("Unrecognised export file type: %s", type(file_bytes_to_export))
        raise ExportError("Unrecognised export file type")
