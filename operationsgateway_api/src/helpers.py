import base64
from io import BytesIO
import json
import logging
from typing import Optional

from PIL import Image
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

        await MongoDBInterface.insert_many("waveforms", waveforms)


# TODO - is async needed?
async def store_images(images):
    for path, data in images.items():
        image = Image.fromarray(data)
        image.save(path)


def create_thumbnails(image_paths):
    thumbnails = {}

    for path in image_paths:
        image = Image.open(path)
        image.thumbnail((50, 50))

        buffered = BytesIO()
        image.save(buffered, format="PNG")

        # TODO - move the base64 encoding into its own function
        image_string = base64.b64encode(buffered.getvalue())
        thumbnails[path] = image_string

    return thumbnails


def store_thumbnails(record, thumbnails):
    # TODO - need to store thumbnails from waveforms - need to create them first
    for image_path, thumbnail in thumbnails.items():
        # TODO - extracting the channel name from the path should be thoroughly unit
        # tested. Probably best to put this code into its own function
        shot_channel = image_path.split("/")[-1].split("_")[1:]
        channel_name = "_".join(shot_channel).split(".")[0]

        record["channels"][channel_name]["thumbnail"] = thumbnail

