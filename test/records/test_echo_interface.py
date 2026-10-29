from io import BytesIO
from typing import AsyncGenerator
from unittest.mock import ANY, AsyncMock, MagicMock, patch

from botocore.exceptions import ClientError
import pytest
import pytest_asyncio

from operationsgateway_api.src.config import Config
from operationsgateway_api.src.exceptions import EchoS3Error
from operationsgateway_api.src.records.echo_interface import EchoInterface, log
from test.conftest import RECORD_ID_05_0800


@pytest_asyncio.fixture(scope="function")
async def echo_interface_with_empty_object() -> AsyncGenerator[EchoInterface, None]:
    bytes_io = BytesIO()
    echo_interface = EchoInterface()
    echo_interface._bucket = await echo_interface.get_bucket()
    await echo_interface.upload_file_object(bytes_io, "empty_object")
    yield echo_interface
    await echo_interface.delete_file_object("empty_object")


@pytest_asyncio.fixture(scope="function")
async def reset_lifecycle() -> AsyncGenerator[None, None]:
    yield

    echo_interface = EchoInterface()
    bucket = await echo_interface.get_bucket()
    lifecycle_configuration = await bucket.LifecycleConfiguration()
    await lifecycle_configuration.delete()


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
    @patch("operationsgateway_api.src.config.Config.config.echo.expiry_days", 1095)
    async def test_put_lifecycle(self, reset_lifecycle: None):
        echo_interface = EchoInterface()
        await echo_interface.put_lifecycle()

        bucket = await echo_interface.get_bucket()
        lifecycle_configuration = await bucket.LifecycleConfiguration()
        rules = await lifecycle_configuration.rules

        assert len(rules) == 1
        assert rules[0] == {
            "Expiration": {"Days": 1095},
            "ID": "expiry",
            "Prefix": "",
            "Status": "Enabled",
        }

    @pytest.mark.asyncio
    async def test_put_lifecycle_unset(self, reset_lifecycle: None):
        log.info = MagicMock(wraps=log.info)
        echo_interface = EchoInterface()
        # expiry_days defaults to None, no PUT sent
        await echo_interface.put_lifecycle()

        msg = "Expiry lifecycle not configured for %s"
        log.info.assert_called_with(msg, Config.config.echo.bucket_name)

    @pytest.mark.asyncio
    # Pydantic config would normally prevent a negative value
    @patch("operationsgateway_api.src.config.Config.config.echo.expiry_days", -1)
    async def test_put_lifecycle_failure(self, reset_lifecycle: None):
        log.exception = MagicMock(wraps=log.exception)
        echo_interface = EchoInterface()
        await echo_interface.put_lifecycle()  # Error on PUT caught and logged

        msg = "Failed to put lifecycle for %s"
        log.exception.assert_called_with(msg, Config.config.echo.bucket_name)

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
        directories_str = EchoInterface.format_record_id(RECORD_ID_05_0800)
        object_path = f"images/{directories_str}/FE-204-NSO-P1-CAM-1.png"
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

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("start_byte", "end_byte"),
        [
            # A byte position cannot be negative
            pytest.param(-1, 5, id="start is negative"),
            # The end cannot come before the start
            pytest.param(10, 5, id="end is before the start"),
        ],
    )
    async def test_download_file_range_invalid_range(
        self,
        start_byte: int,
        end_byte: int,
    ):
        # Rejected before anything is requested, so no bucket is needed
        echo_interface = EchoInterface()

        with pytest.raises(ValueError, match="Invalid byte range"):
            await echo_interface.download_file_range("test", start_byte, end_byte)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("content_range", "data", "expected_message"),
        [
            # 4 to 7 was asked for, but Echo says it sent 0 to 3
            pytest.param(
                "bytes 0-3/100",
                b"abcd",
                "Echo returned an unexpected byte range",
                id="wrong range returned",
            ),
            # 4 bytes were asked for, but only 2 arrived
            pytest.param(
                "bytes 4-7/100",
                b"ab",
                "Expected 4 bytes, received 2",
                id="short read",
            ),
        ],
    )
    async def test_download_file_range_bad_response(
        self,
        content_range: str,
        data: bytes,
        expected_message: str,
    ):
        stream = MagicMock()
        stream.read = AsyncMock(return_value=data)
        body = MagicMock()
        body.__aenter__.return_value = stream
        mock_get_object = AsyncMock(
            return_value={"Body": body, "ContentRange": content_range},
        )
        mock_bucket = MagicMock()
        mock_bucket.meta.client.get_object = mock_get_object
        echo_interface = EchoInterface()
        echo_interface._bucket = mock_bucket

        with pytest.raises(EchoS3Error, match=expected_message):
            await echo_interface.download_file_range("test", 4, 7)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("error_code", "expected_status_code"),
        [
            # boto3 gives the code as a string, and a missing object is a 404
            pytest.param("NoSuchKey", 404, id="object is missing"),
            # Any other failure is a server side problem
            pytest.param("AccessDenied", 500, id="any other error"),
        ],
    )
    async def test_download_file_range_client_error(
        self,
        error_code: str,
        expected_status_code: int,
    ):
        side_effect = ClientError(
            {"Error": {"Code": error_code, "Message": "Failure"}},
            "get_object",
        )
        mock_bucket = MagicMock()
        mock_bucket.meta.client.get_object = AsyncMock(side_effect=side_effect)
        echo_interface = EchoInterface()
        echo_interface._bucket = mock_bucket

        with pytest.raises(EchoS3Error, match=error_code) as exc_info:
            await echo_interface.download_file_range("test", 4, 7)

        assert exc_info.value.status_code == expected_status_code
