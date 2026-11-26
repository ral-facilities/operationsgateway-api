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
from operationsgateway_api.src.records.hdf_export_handler import HdfExportHandler
from operationsgateway_api.src.records.record import Record as Record
from operationsgateway_api.src.routes.common_parameters import ParameterHandler

log = logging.getLogger()
router = APIRouter()
AuthoriseToken = Annotated[str, Depends(authorise_token)]
max_filesize_bytes = Config.config.export.max_filesize_bytes


@router.get(
    "/export",
    summary="Export records using database-like filters",
    response_description="File containing exported data. By default this will be a CSV "
    "file if only scalar values are exported, or a zip file if images "
    "and/or waveforms are included. If `export_hdf` is true it will be a single "
    "HDF5 (.h5) file instead.",
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
        description="Select specific fields in the record e.g. `metadata.shotnum`. "
        "When `export_hdf` is true this is the only thing that selects what goes in "
        "the file, so every channel listed is included whatever its type.",
    ),
    lower_level: Optional[int] = Query(
        0,
        description="The lower level threshold for false colour (0-255). Ignored when "
        "`export_hdf` is true",
        ge=0,
        le=65535,
    ),
    upper_level: Optional[int] = Query(
        255,
        description="The upper level threshold for false colour (0-255). Ignored when "
        "`export_hdf` is true",
        ge=0,
        le=65535,
    ),
    limit_bit_depth: int = Query(
        8,
        description=(
            "The bit depth to which `lower_level` and `upper_level` are relative. This "
            "can be any value as long as it is consistent with the provided levels, "
            "but is intended to reflect the original bit depth of the raw data, so "
            "meaningful values can be displayed and set in the frontend. Ignored when "
            "`export_hdf` is true."
        ),
        ge=0,
        le=16,
    ),
    colourmap_name: Optional[str] = Query(
        None,
        description="The name of the matplotlib colour map to apply to the image"
        " thumbnails. Ignored when `export_hdf` is true",
    ),
    functions: Optional[List[Json]] = Query(
        None,
        description="Functions to evaluate on the record data being returned",
    ),
    export_scalars: Optional[bool] = Query(
        True,
        description="Whether to export the scalar values from the main data table. "
        "Ignored when `export_hdf` is true",
    ),
    export_strings: Optional[bool] = Query(
        True,
        description="Whether to export string values from the main data table. "
        "Ignored when `export_hdf` is true",
    ),
    export_images: Optional[bool] = Query(
        True,
        description="Whether to export the images for image channels. Ignored when "
        "`export_hdf` is true",
    ),
    # Defaults to False, unlike the other channel types, because a series holds every
    # frame and so is far larger than a single image.
    export_image_series: Optional[bool] = Query(
        False,
        description=(
            "Whether to export image series channels. Separate from `export_images`, "
            "and off by default because a series contains every frame and so is much "
            "larger than a single image. Ignored when `export_hdf` is true"
        ),
    ),
    export_float_images: Optional[bool] = Query(
        True,
        description="Whether to export float image channels. Ignored when "
        "`export_hdf` is true",
    ),
    export_waveform_csvs: Optional[bool] = Query(
        True,
        description="Whether to export the waveforms in CSV files. Ignored when "
        "`export_hdf` is true",
    ),
    export_waveform_images: Optional[bool] = Query(
        False,
        description="Whether to export rendered images of the waveforms. Ignored when "
        "`export_hdf` is true",
    ),
    export_vector_csvs: bool = Query(
        True,
        description="Whether to export the vectors in CSV files. Ignored when "
        "`export_hdf` is true",
    ),
    export_vector_images: bool = Query(
        False,
        description="Whether to export images of the vectors. Ignored when "
        "`export_hdf` is true",
    ),
    export_hdf: bool = Query(
        False,
        description=(
            "Whether to return a single HDF5 (.h5) file instead of a CSV or zip file. "
            "Every channel in `projection` is included as raw data, with one group per "
            "record. The `export_*` flags and the false colour parameters are ignored. "
            "Images and image series have the dtype they are stored with (uint8 for a "
            "`bit_depth` of 8 or less, otherwise uint16) and the pixel values they "
            "were ingested with, so a `bit_depth` of 12 gives values up to 4095"
        ),
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

    By default the result is a CSV file, or a zip file if images, waveforms or vectors
    are included. If `export_hdf` is true the result is instead a single HDF5 (.h5) file
    with one group per record, containing every channel listed in `projection` as raw
    data. In that case the `export_*` flags and false colour parameters are ignored.
    Image pixel values are those that were ingested, not the values scaled up to fill
    the 8 or 16 bits they are stored in, so a `bit_depth` of 12 gives values up to 4095.
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

    query_projection = list(projection)

    if export_hdf:
        query_projection = HdfExportHandler.get_projection(projection)
    elif Config.config.export.use_shotnum_in_filenames:
        # Check whether the requested fields already include the shot number.
        includes_metadata = "metadata" in query_projection
        includes_shotnum = "metadata.shotnum" in query_projection

        # Fetch the shot number so we can use it in filenames if not already requested.
        if not includes_metadata and not includes_shotnum:
            query_projection.append("metadata.shotnum")

    records_data = await Record.find_record(
        conditions,
        skip,
        limit,
        query_order,
        query_projection,
    )

    if len(records_data) == 0:
        raise ExportError("No records found to export")

    channel_mainfest = await ChannelManifest.get_most_recent_manifest()

    if export_hdf:
        export_handler = HdfExportHandler(
            records_data,
            channel_mainfest,
            projection,
            functions,
        )
    else:
        export_handler = ExportHandler(
            records_data,
            channel_mainfest,
            projection,
            lower_level,
            upper_level,
            limit_bit_depth,
            colourmap_name,
            functions,
            export_scalars,
            export_strings,
            export_images,
            export_image_series,
            export_float_images,
            export_waveform_csvs,
            export_waveform_images,
            export_vector_csvs=export_vector_csvs,
            export_vector_images=export_vector_images,
        )

    await export_handler.process_records()
    file_bytes_to_export = export_handler.get_export_file_bytes()
    # ensure the "file pointer" is reset
    file_bytes_to_export.seek(0)
    filename = export_handler.get_filename_stem()
    if export_hdf:
        headers = {"Content-Disposition": f'attachment; filename="{filename}.h5"'}
        return Response(
            file_bytes_to_export.read(),
            headers=headers,
            media_type="application/x-hdf5",
        )
    elif isinstance(file_bytes_to_export, io.BytesIO):
        # this is a zip file
        headers = {"Content-Disposition": f'attachment; filename="{filename}.zip"'}
        return Response(
            file_bytes_to_export.read(),
            headers=headers,
            media_type="application/zip",
        )
    elif isinstance(file_bytes_to_export, io.StringIO):
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
