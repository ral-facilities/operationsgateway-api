import base64
from io import BytesIO
import json
import logging
from typing import Optional

from bson import ObjectId
import matplotlib.pyplot as plt
from PIL import Image
import pymongo

from operationsgateway_api.src.config import Config
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


def create_image_plot(x, y, _id):
    plt.plot(x, y)
    plt.savefig(f"/root/seg_dev/og-images/waveforms/{_id}.png")
    # Flushes figure so axes aren't distorted between figures
    plt.clf()


def create_waveform_thumbnails(waveforms):
    # TODO - could probably combine image and waveform thumbnail creation into a single
    # function if the path was given directly/abstracted away
    thumbnails = {}
    for waveform in waveforms:
        waveform_plot = Image.open(
            f"{Config.config.mongodb.image_store_directory}/waveforms/{waveform['_id']}"
            ".png",
        )
        waveform_plot.thumbnail((100, 100))

        # TODO - could be sensible to put the image to base64 stuff (via BytesIO) into
        # its own function
        buffered = BytesIO()
        waveform_plot.save(buffered, format="PNG")
        waveform_string = base64.b64encode(buffered.getvalue())
        thumbnails[waveform["_id"]] = waveform_string

    return thumbnails


def store_waveform_thumbnails(record, thumbnails):
    # TODO - fairly scruffy code, I'd like to have the channel name given to this
    # function really. Or combining it with the image version of this function so we can
    # abstract fetching the channel name
    for _id, thumbnail in thumbnails.items():
        for channel_name, value in record["channels"].items():
            try:
                if ObjectId(_id) == value["waveform_id"]:
                    record["channels"][channel_name]["thumbnail"] = thumbnail
            except KeyError:
                # A KeyError here will be because the channel isn't a waveform. This is
                # normal behaviour and is acceptable to pass
                pass


def truncate_thumbnail_output(record):
    for value in record["channels"].values():
        try:
            value["thumbnail"] = value["thumbnail"][:50]
        except KeyError:
            # If there's no thumbnails (e.g. if channel isn't an image or waveform) then
            # a KeyError will be raised. This is normal behaviour, so acceptable to pass
            pass
