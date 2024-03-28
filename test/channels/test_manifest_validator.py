from tempfile import SpooledTemporaryFile
from unittest.mock import patch

import pytest

from operationsgateway_api.src.channels.channel_manifest import ChannelManifest
from operationsgateway_api.src.exceptions import ChannelManifestError


class TestManifestValidator:
    @pytest.mark.asyncio
    async def test_channel_removed(self):

        spooled_file = SpooledTemporaryFile()
        content = (
            '{"_id": "19830222132431", "channels": {"PM-201-FE-CAM-1": '
            '{"name": "D100 front-end NF", "path": "/PM-201/FE", "type": "image"}, '
            '"PM-201-FE-CAM-2": {"name": "D100 front-end FF", "path": "/PM-201/FE",'
            ' "type": "image"}}}'
        )
        spooled_file.write(content.encode())
        spooled_file.seek(0)

        instance = ChannelManifest(manifest_input=spooled_file)

        with pytest.raises(
            ChannelManifestError,
            match="has been removed from the input channel metadata",
        ):
            await instance.validate(bypass_channel_check=False)

    @pytest.mark.asyncio
    async def test_unmatched_channel_field(self):

        spooled_file = SpooledTemporaryFile()
        content = (
            '{"_id": "19830222132431", "channels": {"PM-201-FE-CAM-1": '
            '{"name": "D100 front-end NF", "path": "/PM-201/FE", "type": "image"}, '
            '"PM-201-FE-CAM-2": {"name": "D100 front-end FF", "path": "/PM-201/FE",'
            ' "type": "image"}}}'
        )
        spooled_file.write(content.encode())
        spooled_file.seek(0)

        instance = ChannelManifest(manifest_input=spooled_file)

        altered_content = {
            "_id": "19830222132431",
            "channels": {
                "PM-201-FE-CAM-1": {
                    "name": "D100 front-end NF",
                    "path": "/PM-201/FE",
                    "type": "image",
                },
                "PM-201-FE-CAM-2": {
                    "name": "D100 front-end FF",
                    "path": "/PM-201/FE",
                    "type": "waveform",
                },
            },
        }

        with patch(
            "operationsgateway_api.src.channels.channel_manifest.ChannelManifest."
            "get_most_recent_manifest",
            return_value=altered_content,
        ):
            with pytest.raises(ChannelManifestError, match="has been modified on the"):
                await instance.validate(bypass_channel_check=False)

    @pytest.mark.asyncio
    async def test_stored_channel_missing(self):

        spooled_file = SpooledTemporaryFile()
        content = (
            '{"_id": "19830222132431", "channels": {"PM-201-FE-CAM-1": '
            '{"name": "D100 front-end NF", "path": "/PM-201/FE", "type": "image"}, '
            '"PM-201-FE-CAM-2": {"name": "D100 front-end FF", "path": "/PM-201/FE",'
            ' "type": "image"}}}'
        )
        spooled_file.write(content.encode())
        spooled_file.seek(0)

        instance = ChannelManifest(manifest_input=spooled_file)

        altered_content = {
            "_id": "19830222132431",
            "channels": {
                "PM-201-FE-CAM-1": {
                    "name": "D100 front-end NF",
                    "path": "/PM-201/FE",
                    "type": "image",
                },
            },
        }

        with patch(
            "operationsgateway_api.src.channels.channel_manifest.ChannelManifest."
            "get_most_recent_manifest",
            return_value=altered_content,
        ):
            await instance.validate(bypass_channel_check=False)
