import logging
from typing import List

from fastapi import APIRouter, Depends, Path, Query
from pydantic import Json
from typing_extensions import Annotated


from operationsgateway_api.src.auth.authorisation import authorise_token
from operationsgateway_api.src.error_handling import endpoint_error_handling
from operationsgateway_api.src.records.image import Image
from operationsgateway_api.src.records.record import Record
from operationsgateway_api.src.records.waveform import Waveform


log = logging.getLogger()
router = APIRouter()


@router.get(
    "/waveforms/{record_id}/{channel_name}",
    summary="Get a waveform object, specified by record ID and channel name",
    response_description="Single waveform object",
    tags=["Waveforms"],
)
@endpoint_error_handling
async def get_waveform_by_id(
    record_id: Annotated[
        str,
        Path(
            ...,
            description="ID of the record (usually timestamp)",
        ),
    ],
    channel_name: Annotated[
        str,
        Path(
            ...,
            description="Channel name containing the waveform",
        ),
    ],
    access_token: Annotated[str, Depends(authorise_token)],
):
    """
    This endpoint gets a single waveform object by channel name and the record ID that
    the waveform belongs to. These two pieces of data form the waveform ID. You can find
    the ID of a waveform object by finding the `waveform_id` field on a waveform channel
    in a record object. `waveform_id` is simply a reference to a waveform which is
    stored in a different collection/table
    """

    waveform_id = f"{record_id}_{channel_name}"

    log.info("Getting waveform by ID: %s", waveform_id)

    return await Waveform.get_waveform(waveform_id)


@router.get(
    "/waveforms/function/{record_id}/{function_name}",
    summary="Get a waveform object from a function",
    response_description="Single waveform object",
    tags=["Waveforms"],
)
@endpoint_error_handling
async def get_waveform_from_function(
    record_id: Annotated[
        str,
        Path(
            ...,
            description="ID of the record (usually timestamp)",
        ),
    ],
    function_name: Annotated[
        str,
        Path(
            ...,
            description="Function name returning the waveform",
        ),
    ],
    access_token: Annotated[str, Depends(authorise_token)],
    functions: List[Json] = Query(
        None,
        description="Functions to evaluate on the record data being returned",
    ),
):
    """
    This endpoint returns a single waveform object by specifying a
    `function_name` corresponding to an entry in `functions` and the record ID.
    Other entries should correspond to functions upon which the desired function
    depends.
    """
    log.info("Getting waveform from function for record ID: %s", record_id)

    record = {"_id": record_id}
    colourmap_name = await Image.get_preferred_colourmap(access_token)
    await Record.apply_functions(
        record,
        functions,
        0,
        255,
        colourmap_name,
        truncate_response=False,
    )

    return record["channels"][function_name]["data"]
