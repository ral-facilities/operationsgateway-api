import argparse
import asyncio

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
import pymongo

from operationsgateway_api.src.config import Config
from operationsgateway_api.src.records.echo_interface import EchoInterface
from operationsgateway_api.src.records.image import Image
from operationsgateway_api.src.records.waveform import Waveform

parser = argparse.ArgumentParser()
parser.add_argument(
    "-u",
    "--url",
    type=str,
    help="URL of database",
    default="mongodb://localhost:27017",
)
parser.add_argument(
    "-n",
    "--database-name",
    type=str,
    help="Name of database",
    default="opsgateway",
)
parser.add_argument(
    "-l",
    "--limit",
    type=int,
    help="Number of records to move data for",
    default=1,
)

args = parser.parse_args()
DATABASE_CONNECTION_URL = args.url
DATABASE_NAME = args.database_name
BUCKET_NAME = Config.config.echo.bucket_name
LIMIT = args.limit


async def move_object(
    echo_interface: EchoInterface,
    records: AsyncIOMotorCollection,
    channel_name: str,
    path_key: str,
    file_extension: str,
    controller: Image | Waveform,
) -> None:
    field = f"channels.{channel_name}.{path_key}"
    regex_value = r"^\d{14}\/" + channel_name + r"\." + file_extension + r"$"
    regex_filter = {field: {"$regex": regex_value}}
    cursor = records.find(filter=regex_filter, projection=[field], limit=LIMIT)
    async for model in cursor:
        record_id = model["_id"]
        old_path = model["channels"][channel_name][path_key]
        old_full_path = controller.get_full_path(relative_path=old_path)
        new_path = controller.get_relative_path(record_id, channel_name, True)
        full_new_path = controller.get_full_path(new_path)

        copy_source = {"Bucket": Config.config.echo.bucket_name, "Key": old_full_path}
        update = {"$set": {f"channels.{channel_name}.{path_key}": new_path}}
        delete = {"Objects": [{"Key": old_full_path}]}
        echo_interface.bucket.copy(CopySource=copy_source, Key=full_new_path)
        records.update_one(filter={"_id": record_id}, update=update)
        echo_interface.bucket.delete_objects(Delete=delete)


async def main():
    echo_interface = EchoInterface()
    client = AsyncIOMotorClient(DATABASE_CONNECTION_URL)
    db = client[DATABASE_NAME]
    channels_manifests = db.get_collection("channels")
    records = db.get_collection("records")
    sort = [("_id", pymongo.DESCENDING)]
    channels_manifest = await channels_manifests.find_one(sort=sort)
    for channel_name, channel_model in channels_manifest["channels"].items():
        if channel_model["type"] == "image":
            print("Processing image channel:", channel_name)
            await move_object(
                echo_interface,
                records,
                channel_name,
                path_key="image_path",
                file_extension="png",
                controller=Image,
            )
        elif channel_model["type"] == "waveform":
            print("Processing waveform channel:", channel_name)
            await move_object(
                echo_interface,
                records,
                channel_name,
                path_key="waveform_path",
                file_extension="json",
                controller=Waveform,
            )


if __name__ == "__main__":
    asyncio.run(main())
