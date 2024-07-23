import json
from tempfile import SpooledTemporaryFile
from unittest.mock import patch

import pytest

from operationsgateway_api.src.channels.channel_manifest import ChannelManifest
from operationsgateway_api.src.exceptions import ChannelManifestError, ModelError
from operationsgateway_api.src.models import ChannelManifestModel
from operationsgateway_api.src.mongo.interface import MongoDBInterface


success_manifest_content = (
    '{"_id": "19830222132431", "channels": {"PM-201-FE-CAM-1": '
    '{"name": "D100 front-end NF", "path": "/PM-201/FE", "type": "image"}, '
    '"PM-201-FE-CAM-2": {"name": "D100 front-end FF", "path": "/PM-201/FE",'
    ' "type": "image"}}}'
)


def get_spooled_file(fail_type=0):
    spooled_file = SpooledTemporaryFile()

    if fail_type == 1:
        content = (
            '{"_id": "19830222132431, "channels": {"PM-201-FE-CAM-1": '
            '{"name": "D100 front-end NF", "path": "/PM-201/FE", "type": "image"}, '
            '"PM-201-FE-CAM-2": {"name": "D100 front-end FF", "path": "/PM-201/FE",'
            ' "type": "image"}}}'
        )
    elif fail_type == 2:
        content = "{}"
    else:
        content = success_manifest_content
    spooled_file.write(content.encode())
    spooled_file.seek(0)

    return ChannelManifest(manifest_input=spooled_file)


class TestChannelManifest:
    @pytest.mark.asyncio
    async def test_get_channel_fail(self):
        with pytest.raises(
            ChannelManifestError,
            match="Channel 'non_existant_channel' cannot be found",
        ):
            await ChannelManifest.get_channel(channel_name="non_existant_channel")

    @pytest.mark.asyncio
    async def test_decode_error(self):
        with pytest.raises(
            ChannelManifestError,
            match="Channel manifest file not valid JSON",
        ):
            get_spooled_file(fail_type=1)

    @pytest.mark.asyncio
    async def test_manifest_validation_error(self):
        with pytest.raises(ModelError):
            get_spooled_file(fail_type=2)

    @pytest.mark.asyncio
    async def test_validate_pass(self):
        instance = get_spooled_file()

        await instance.validate(bypass_channel_check=True)

    @pytest.mark.asyncio
    async def test_validate_no_stored_file(self):
        instance = get_spooled_file()

        with patch(
            "operationsgateway_api.src.channels.channel_manifest.ChannelManifest"
            ".get_most_recent_manifest",
            return_value=None,
        ):
            await instance.validate(bypass_channel_check=True)

    @pytest.mark.asyncio
    async def test_insert_success(self, remove_manifest_entry):
        with patch(
            "operationsgateway_api.src.channels.channel_manifest.ChannelManifest._add_id",
            return_value="19830222132431",
        ):
            instance = get_spooled_file()

            await instance.insert()

            channel_manifest = await MongoDBInterface.find_one(
                "channels",
                {"_id": "19830222132431"},
            )
            expected_manifest = json.loads(success_manifest_content)
            assert channel_manifest == expected_manifest

    @pytest.mark.parametrize(
        "data, expected_return",
        [
            pytest.param(
                json.loads(success_manifest_content),
                ChannelManifestModel(**json.loads(success_manifest_content)),
                id="Typical dictionary input",
            ),
            pytest.param(None, None, id="Empty input"),
        ],
    )
    def test_use_model(self, data, expected_return):
        model = ChannelManifest._use_model(data)
        assert model == expected_return
