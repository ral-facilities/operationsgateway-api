from http import HTTPStatus
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, Path, Query, Response
from pydantic import Json
from typing_extensions import Annotated

from operationsgateway_api.src.auth.authorisation import (
    authorise_route,
    authorise_token,
)
from operationsgateway_api.src.error_handling import endpoint_error_handling
from operationsgateway_api.src.exceptions import QueryParameterError
from operationsgateway_api.src.records.record import Record as Record
from operationsgateway_api.src.routes.common_parameters import ParameterHandler


log = logging.getLogger()
router = APIRouter()
AuthoriseToken = Annotated[str, Depends(authorise_token)]


@router.get(
    "/records",
    summary="Get records using database-like filters",
    response_description="List of records",
    tags=["Records"],
)
@endpoint_error_handling
async def get_records(
    access_token: AuthoriseToken,
    conditions: Json = Query(
        {},
        description="Conditions to apply to the query",
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
    truncate: Optional[bool] = Query(
        False,
        description="Parameter used for development to reduce the output of"
        " thumbnail strings to 50 characters",
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
):
    """
    This endpoint uses MongoDB's find() method to query the records
    collection. As a result, this endpoint exposes some of this functionality, which
    you can find more information about at:
    https://www.mongodb.com/docs/manual/reference/method/db.collection.find
    """

    log.info("Getting records by query")

    query_order = list(ParameterHandler.extract_order_data(order)) if order else ""
    ParameterHandler.encode_date_for_conditions(conditions)

    records_data = await Record.find_record(
        conditions,
        skip,
        limit,
        query_order,
        projection,
    )

    for record_data in records_data:
        if record_data.get("channels"):
            await Record.apply_false_colour_to_thumbnails(
                record_data,
                lower_level,
                upper_level,
                colourmap_name,
            )

            if truncate:
                Record.truncate_thumbnails(record_data)

    return records_data


@router.get(
    "/records/count",
    summary="Count the number of records stored based on given conditions to restrict"
    " the search",
    response_description="Record count",
    tags=["Records"],
)
@endpoint_error_handling
async def count_records(
    access_token: AuthoriseToken,
    conditions: Json = Query({}, description="Conditions to apply to the query"),
):
    """
    This endpoint uses the `conditions` query parameter (i.e. like a WHERE filter) in
    the same way as GET `/records`. For example, there is a WHERE filter is not
    applicable to a GET by ID request in DataGateway API
    """

    log.info("Counting records using given conditions")
    ParameterHandler.encode_date_for_conditions(conditions)

    return await Record.count_records(conditions)


@router.get(
    "/records/range_converter",
    summary="Convert shot number range to date range and vice versa",
    response_description="Range opposite to input",
    tags=["Records"],
)
@endpoint_error_handling
async def convert_search_ranges(
    access_token: AuthoriseToken,  # noqa: B008
    shotnum_range: Json = Query(
        {},
        description='Min and max shot number range (e.g. {"min": 200, "max": 500})',
    ),
    date_range: Json = Query(
        {},
        description="From and to date range (e.g."
        ' {"from": "2022-04-07 14:16:19", "to": "2022-04-07 21:00:00"})',
    ),
):
    if date_range and shotnum_range:
        raise QueryParameterError(
            "Query parameters cannot contain both date_range and shotnum_range",
        )

    return await Record.convert_search_ranges(date_range, shotnum_range)


@router.get(
    "/records/{id_}",
    summary="Get a record specified by its ID",
    response_description="Single record object",
    tags=["Records"],
)
@endpoint_error_handling
async def get_record_by_id(
    access_token: AuthoriseToken,
    id_: Annotated[
        str,
        Path(
            ...,
            description="`_id` of the record to fetch from the database",
        ),
    ],
    conditions: Json = Query({}, description="Conditions to apply to the query"),
    truncate: Optional[bool] = Query(
        False,
        description="Parameter used for development to reduce the output of"
        " thumbnail strings to 50 characters",
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
):
    """
    Get a single record by its ID. The `conditions` query parameter exists but a
    specific use case is uncertain at this stage because the ID is the element that
    tells MongoDB which record to retrieve
    """

    log.info("Getting record by ID: %s", id_)

    record_data = await Record.find_record_by_id(id_, conditions)

    if record_data.get("channels"):
        await Record.apply_false_colour_to_thumbnails(
            record_data,
            lower_level,
            upper_level,
            colourmap_name,
        )

    if truncate:
        Record.truncate_thumbnails(record_data)

    return record_data


@router.delete(
    "/records/{id_}",
    summary="Delete a record specified by its ID",
    response_description="No content",
    status_code=204,
    tags=["Records"],
)
@endpoint_error_handling
async def delete_record_by_id(
    id_: Annotated[
        str,
        Path(
            ...,
            description="`_id` of the record to delete from the database",
        ),
    ],
    access_token: Annotated[str, Depends(authorise_route)],
):
    # TODO 2 - full implementation will require searching through waveform channels to
    # remove the documents in the waveforms collection. The images will need to be
    # removed from disk too
    log.info("Deleting record by ID: %s", id_)

    await Record.delete_record(id_)

    return Response(status_code=HTTPStatus.NO_CONTENT.value)
