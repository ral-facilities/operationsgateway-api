from http import HTTPStatus
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, Path, Query, Response

from operationsgateway_api.src.error_handling import endpoint_error_handling
from operationsgateway_api.src.records.record import Record as Record
from operationsgateway_api.src.routes.common_parameters import ParameterHandler


log = logging.getLogger()
router = APIRouter()


@router.get(
    "/records",
    summary="Get records using database-like filters",
    response_description="List of records",
    tags=["Records"],
)
@endpoint_error_handling
async def get_records(
    # TODO - investigate linting errors
    conditions: dict = Depends(ParameterHandler.filter_conditions),  # noqa: B008
    skip: int = Query(  # noqa: B008
        0,
        description="How many documents should be skipped before returning results",
    ),
    limit: int = Query(  # noqa: B008
        0,
        description="How many documents the result should be limited to",
    ),
    order: Optional[List[str]] = Query(  # noqa: B008
        None,
        description="Specify order of results in the format of `field_name ASC`",
        examples={
            "asc": {
                "summary": "Shot number ascending",
                "value": "metadata.shotnum ASC",
            },
            "desc": {"summary": "ID descending", "value": "_id DESC"},
        },
    ),
    projection: Optional[List[str]] = Query(  # noqa: B008
        None,
        description="Select specific fields in the record e.g. `metadata.shotnum`",
        examples={
            "metadata": {"summary": "Shot number", "value": "metadata.shotnum"},
            "channel_data": {"summary": "Channel data", "value": "channels.data"},
        },
    ),
    truncate: Optional[bool] = Query(  # noqa: B008
        False,
        description="Parameter used for development to reduce the output of thumbnail"
        " strings to 50 characters",
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

    if truncate:
        for record_data in records_data:
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
    conditions: dict = Depends(ParameterHandler.filter_conditions),  # noqa: B008
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
    "/records/{id_}",
    summary="Get a record specified by its ID",
    response_description="Single record object",
    tags=["Records"],
)
@endpoint_error_handling
async def get_record_by_id(
    id_: str = Path(  # noqa: B008
        ...,
        description="`_id` of the record to fetch from the database",
    ),
    conditions: dict = Depends(ParameterHandler.filter_conditions),  # noqa: B008
    truncate: Optional[bool] = Query(  # noqa: B008
        False,
        description="Parameter used for development to reduce the output of thumbnail"
        " strings to 50 characters",
    ),
):
    """
    Get a single record by its ID. The `conditions` query parameter exists but a
    specific use case is uncertain at this stage because the ID is the element that
    tells MongoDB which record to retrieve
    """

    log.info("Getting record by ID: %s", id_)

    record_data = await Record.find_record_by_id(id_, conditions)

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
    id_: str = Path(  # noqa: B008
        ...,
        description="`_id` of the record to delete from the database",
    ),
):
    # TODO 2 - full implementation will require searching through waveform channels to
    # remove the documents in the waveforms collection. The images will need to be
    # removed from disk too
    log.info("Deleting record by ID: %s", id_)

    await Record.delete_record(id_)

    return Response(status_code=HTTPStatus.NO_CONTENT.value)
