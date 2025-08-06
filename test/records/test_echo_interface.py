from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

from botocore.exceptions import ClientError
from pydantic import SecretStr
import pytest

from operationsgateway_api.src.exceptions import EchoS3Error
from operationsgateway_api.src.records.echo_interface import EchoInterface


class TestEchoInterface:
    @pytest.mark.asyncio
    async def test_get_bucket(self):
        target = "operationsgateway_api.src.config.Config.config.echo.bucket_name"
        match = "Bucket for object storage cannot be found"
        echo_interface = EchoInterface()
        with patch(target, "test"):
            with pytest.raises(EchoS3Error, match=match):
                await echo_interface.get_bucket()

    @pytest.mark.asyncio
    async def test_invalid_upload_file_object(self):
        side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
            "upload_fileobj",
        )
        mock_upload_fileobj = AsyncMock(side_effect=side_effect)
        mock_bucket = MagicMock()
        mock_bucket.upload_fileobj = mock_upload_fileobj
        echo_interface = EchoInterface()
        echo_interface._bucket = mock_bucket
        with pytest.raises(EchoS3Error, match="when uploading file at"):
            await echo_interface.upload_file_object(BytesIO(), "test")

    @pytest.mark.asyncio
    async def test_invalid_delete_file_object(self):
        side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
            "delete_fileobj",
        )
        mock_object = AsyncMock(side_effect=side_effect)
        mock_bucket = MagicMock()
        mock_bucket.Object = mock_object
        echo_interface = EchoInterface()
        echo_interface._bucket = mock_bucket
        with pytest.raises(EchoS3Error, match="when deleting file at"):
            await echo_interface.delete_file_object("test")

    @pytest.mark.asyncio
    async def test_invalid_delete_directory(self):
        side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
            "filter",
        )
        mock_filter = MagicMock(side_effect=side_effect)
        mock_objects = MagicMock()
        mock_objects.filter = mock_filter
        mock_bucket = MagicMock()
        mock_bucket.objects = mock_objects
        echo_interface = EchoInterface()
        echo_interface._bucket = mock_bucket
        with pytest.raises(EchoS3Error, match="when deleting directory"):
            await echo_interface.delete_directory("test")
