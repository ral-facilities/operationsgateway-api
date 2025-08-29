from io import BytesIO
from typing import AsyncGenerator
from unittest.mock import ANY, AsyncMock, MagicMock, patch

from botocore.exceptions import ClientError
import pytest
import pytest_asyncio

from operationsgateway_api.src.exceptions import EchoS3Error
from operationsgateway_api.src.records.echo_interface import EchoInterface, log


@pytest_asyncio.fixture(scope="function")
async def echo_interface_with_empty_object() -> AsyncGenerator[EchoInterface, None]:
    bytes_io = BytesIO()
    echo_interface = EchoInterface()
    echo_interface._bucket = await echo_interface.get_bucket()
    await echo_interface.upload_file_object(bytes_io, "empty_object")
    yield echo_interface
    await echo_interface.delete_file_object("empty_object")


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
    async def test_empty_download_file_object(
        self,
        echo_interface_with_empty_object: EchoInterface,
    ):
        log.warning = MagicMock(wraps=log.warning)

        await echo_interface_with_empty_object.download_file_object("empty_object")

        msg = (
            "Bytes array from downloaded object is empty, "
            "file download from S3 might have been unsuccessful: %s"
        )
        log.warning.assert_called_once_with(msg, "empty_object")

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

    @pytest.mark.asyncio
    async def test_head_object(self):
        echo_interface = EchoInterface()
        echo_interface._bucket = await echo_interface.get_bucket()
        assert not await echo_interface.head_object("test")

    @pytest.mark.asyncio
    async def test_cached_bytes(self):
        echo_interface = EchoInterface()
        echo_interface._bucket = await echo_interface.get_bucket()
        echo_interface._bucket.download_fileobj = MagicMock(
            wraps=echo_interface._bucket.download_fileobj,
        )
        # First call results in download
        object_path = "images/2023/06/05/100000/FE-204-NSO-P1-CAM-1.png"
        await echo_interface.download_file_object(object_path)
        echo_interface._bucket.download_fileobj.assert_called_once_with(
            Fileobj=ANY,
            Key=object_path,
        )
        # Second call does not result in an additional download as bytes are cached
        await echo_interface.download_file_object(object_path)
        echo_interface._bucket.download_fileobj.assert_called_once_with(
            Fileobj=ANY,
            Key=object_path,
        )
