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
    functions: List[Json] = Query(
        None,
        description="Functions to evaluate on the record data being returned",
    ),
):
    """
    This endpoint gets a single waveform object by channel name and the record ID that
    the waveform belongs to. These two pieces of data form the waveform ID. You can find
    the ID of a waveform object by finding the `waveform_id` field on a waveform channel
    in a record object. `waveform_id` is simply a reference to a waveform which is
    stored in a different collection/table.

    If `channel_name` matches one of the entries in `functions`, then that will be
    evaluated to generate the returned waveform.
    """
    if functions:
        for function_dict in functions:
            if function_dict["name"] == channel_name:
                log.info("Getting waveform from function for record ID: %s", record_id)

                record = {"_id": record_id}
                colourmap_name = await Image.get_preferred_colourmap(access_token)
                await Record.apply_functions(
                    record=record,
                    functions=functions,
                    original_image=False,
                    lower_level=0,
                    upper_level=255,
                    limit_bit_depth=8,  # Limits hardcoded to 8 bit
                    colourmap_name=colourmap_name,
                    return_thumbnails=False,
                )

                return record["channels"][channel_name]["data"]

    waveform_path = Waveform.get_relative_path(record_id, channel_name)
    log.info("Getting waveform by path: %s", waveform_path)
    return Waveform.get_waveform(waveform_path)
