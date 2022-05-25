import json
import logging
from typing import Optional

import pymongo

from operationsgateway_api.src.data_encoding import DataEncoding
from operationsgateway_api.src.mongo.interface import MongoDBInterface

log = logging.getLogger()

async def filter_conditions(
    conditions: Optional[str] = None,
):
    """
    Converts a JSON string that comes from a query parameter into a Python dictionary

    FastAPI doesn't directly support dictionary query parameters, so they must be
    converted using `json.loads()` and 'injected' into the endpoint function using
    `Depends()`
    """

    log.debug(f"Conditions: {conditions}, Type: {type(conditions)}")

    return json.loads(conditions) if conditions is not None else {}


def extract_order_data(orders):
    """
    Given a string of the order portion of a MongoDB query, put it into a format that
    PyMongo can understand

    An example input string: `[channel_name.title asc, shotnum desc]`
    """

    sort_data = []

    for order in orders:
        field = order.split(" ")[0]
        direction = order.split(" ")[1]

        if direction.lower() == "asc":
            direction = pymongo.ASCENDING
        elif direction.lower() == "desc":
            direction = pymongo.DESCENDING
        else:
            raise ValueError(
                "Invalid direction given in order parameter, please try again",
            )

        sort_data.append((field, direction))

    return sort_data


def is_shot_stored(document):
    return True if document else False


async def insert_waveforms(waveforms):
    if waveforms:
        for waveform in waveforms:
            DataEncoding.encode_numpy_for_mongo(waveform)

        log.debug("Waveforms: %s, Length: %s", waveforms, len(waveforms))
        await MongoDBInterface.insert_many("waveforms", waveforms)
