import base64
from datetime import datetime
from io import BytesIO
import json
import logging
from typing import Optional

from bson import ObjectId
from dateutil.parser import parse
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


def is_shot_stored(document):
    return True if document else False


async def insert_waveforms(waveforms):
    if waveforms:
        for waveform in waveforms:
            DataEncoding.encode_numpy_for_mongo(waveform)

        await MongoDBInterface.insert_many("waveforms", waveforms)


def store_images(images):
    for path, data in images.items():
        image = Image.fromarray(data)
        image.save(path)


def create_image_thumbnails(image_paths):
    thumbnails = {}

    for path in image_paths:
        image = Image.open(path)
        create_thumbnail(image, Config.config.app.image_thumbnail_size)
        thumbnails[path] = convert_image_to_base64(image)

    return thumbnails


def store_image_thumbnails(record, thumbnails):
    for image_path, thumbnail in thumbnails.items():
        # TODO - extracting the channel name from the path should be thoroughly unit
        # tested. Probably best to put this code into its own function
        shot_channel = image_path.split("/")[-1].split("_")[1:]
        channel_name = "_".join(shot_channel).split(".")[0]

        record["channels"][channel_name]["thumbnail"] = thumbnail


def create_image_plot(x, y, buf):
    plt.plot(x, y)
    plt.savefig(buf, format="PNG")
    # Flushes figure so axes aren't distorted between figures
    plt.clf()


def create_thumbnail(image: Image.Image, max_size: tuple) -> None:
    image.thumbnail(max_size)


def convert_image_to_base64(image: Image.Image) -> bytes:
    with BytesIO() as buf:
        image.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue())


def create_waveform_thumbnails(waveforms):
    thumbnails = {}

    for waveform in waveforms:
        with BytesIO() as plot_buffer:
            # TODO - S307 linting error
            create_image_plot(
                list(eval(waveform["x"])),  # noqa: S307
                list(eval(waveform["y"])),  # noqa: S307
                plot_buffer,
            )
            waveform_image = Image.open(plot_buffer)
            create_thumbnail(waveform_image, Config.config.app.waveform_thumbnail_size)

            thumbnails[waveform["_id"]] = convert_image_to_base64(waveform_image)

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
