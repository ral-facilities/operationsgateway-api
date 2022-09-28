import base64
from datetime import datetime
from io import BytesIO
import json
import logging
import os
from typing import Optional

from dateutil.parser import parse
import matplotlib.pyplot as plt
from PIL import Image
import pymongo

from operationsgateway_api.src.config import Config
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


def encode_date_for_conditions(value):
    new_date = None

    if isinstance(value, dict):
        for inner_key, inner_value in value.items():
            new_new_date = encode_date_for_conditions(inner_value)
            if new_new_date is not None:
                value[inner_key] = new_new_date
    elif isinstance(value, list):
        for element in value:
            encode_date_for_conditions(element)
    elif isinstance(value, str):
        try:
            parse(value, fuzzy=False)

            new_date = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            # Not a date, nothing to do here
            pass

        return new_date


def truncate_thumbnail_output(record):
    for value in record["channels"].values():
        try:
            value["thumbnail"] = value["thumbnail"][:50]
        except KeyError:
            # If there's no thumbnails (e.g. if channel isn't an image or waveform) then
            # a KeyError will be raised. This is normal behaviour, so acceptable to pass
            pass
