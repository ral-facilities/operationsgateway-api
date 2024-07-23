from unittest.mock import patch

import pytest

from operationsgateway_api.src.exceptions import ChannelManifestError
from operationsgateway_api.src.models import ChannelManifestModel


class TestManifestValidator:
    @pytest.mark.asyncio
    async def test_channel_removed(self, create_manifest_file):
        with pytest.raises(
            ChannelManifestError,
            match="has been removed from the input channel metadata",
        ):
            await create_manifest_file.validate(bypass_channel_check=False)

    @pytest.mark.asyncio
    async def test_unmatched_channel_field(self, create_manifest_file):
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
        altered_manifest = ChannelManifestModel(**altered_content)

        with patch(
            "operationsgateway_api.src.channels.channel_manifest.ChannelManifest."
            "get_most_recent_manifest",
            return_value=altered_manifest,
        ):
            with pytest.raises(ChannelManifestError, match="has been modified on the"):
                await create_manifest_file.validate(bypass_channel_check=False)

    @pytest.mark.asyncio
    async def test_stored_channel_missing(self, create_manifest_file):
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
        altered_manifest = ChannelManifestModel(**altered_content)

        with patch(
            "operationsgateway_api.src.channels.channel_manifest.ChannelManifest."
            "get_most_recent_manifest",
            return_value=altered_manifest,
        ):
            await create_manifest_file.validate(bypass_channel_check=False)
