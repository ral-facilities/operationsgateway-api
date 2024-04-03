from tempfile import SpooledTemporaryFile

import pytest
import pytest_asyncio

from operationsgateway_api.src.channels.channel_manifest import ChannelManifest
from operationsgateway_api.src.mongo.interface import MongoDBInterface


@pytest_asyncio.fixture(scope="function")
async def remove_manifest_entry():
    yield
    await MongoDBInterface.delete_one(
        "channels",
        filter_={"_id": "19830222132431"},
    )


@pytest.fixture(scope="function")
def create_manifest_file():
    spooled_file = SpooledTemporaryFile()
    content = (
        '{"_id": "19830222132431", "channels": {"PM-201-FE-CAM-1": '
        '{"name": "D100 front-end NF", "path": "/PM-201/FE", "type": "image"}, '
        '"PM-201-FE-CAM-2": {"name": "D100 front-end FF", "path": "/PM-201/FE",'
        ' "type": "image"}}}'
    )
    spooled_file.write(content.encode())
    spooled_file.seek(0)

    channel_manifest = ChannelManifest(manifest_input=spooled_file)
    yield channel_manifest
