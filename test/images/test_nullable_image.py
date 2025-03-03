import base64
from io import BytesIO
from unittest.mock import patch

import imagehash
import numpy as np
from PIL import Image
import pytest

from operationsgateway_api.src.exceptions import (
    EchoS3Error,
    ImageError,
    ImageNotFoundError,
)
from operationsgateway_api.src.models import NullableImageModel
from operationsgateway_api.src.records.nullable_image import NullableImage


class TestImage:
    config_echo_url = "https://mytesturl.com"
    config_echo_access_key = "TestAccessKey"
    config_echo_secret_key = "TestSecretKey"
    config_image_bucket_name = "MyTestBucket"
    path = "test/image/path.png"
    data = np.array([[np.nan, 1], [-0.5, 0]], dtype=np.float32)
    model = NullableImageModel(path=path, data=data)
    stored_bytes = (
        b"PK\x03\x04-\x00\x00\x00\x08\x00\x00\x00!\x00*\x8ch\xc8\xff\xff\xff\xff\xff"
        b"\xff\xff\xff\t\x00\x14\x00arr_0.npy\x01\x00\x10\x00\x90\x00\x00\x00\x00\x00"
        b"\x00\x00U\x00\x00\x00\x00\x00\x00\x00\x9b\xec\x17\xea\x1b\x10\xc9\xc8P\xc6"
        b"P\xad\x9e\x92Z\x9c\\\xa4n\xa5\xa0n\x93f\xa2\xae\xa3\xa0\x9e\x96_TR\x94\x98"
        b"\x17\x9f_\x94\x92\n\x12wK\xcc)N\x05\x8a\x17g$\x16\xa4\x02\xf9\x1aF:\nF\x9a:\n"
        b"\xb5\nd\x03.\x06\x86\x03\xf5\x0c\x0c\r\xf6\x0c\x0c\x0c\xfb\x81\x98\x01\x00PK"
        b"\x01\x02-\x03-\x00\x00\x00\x08\x00\x00\x00!\x00*\x8ch\xc8U\x00\x00\x00\x90"
        b"\x00\x00\x00\t\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x80\x01\x00\x00"
        b"\x00\x00arr_0.npyPK\x05\x06\x00\x00\x00\x00\x01\x00\x01\x007\x00\x00\x00\x90"
        b"\x00\x00\x00\x00\x00"
    )

    @pytest.mark.parametrize(
        ["data", "phash"],
        [
            pytest.param(data, "9e9e5a5a5a5849a5"),
            pytest.param(
                np.array([[np.nan, np.nan], [np.nan, np.nan]], dtype=np.float32),
                "0000000000000000",
            ),
            pytest.param(
                np.array([[0, 0], [0, 0]], dtype=np.float32),
                "8000000000000000",
            ),
        ],
    )
    def test_create_thumbnail(self, data: np.ndarray, phash: str):
        test_image = NullableImage(NullableImageModel(path=self.path, data=data))
        test_image.create_thumbnail()
        bytes_thumbnail = base64.b64decode(test_image.thumbnail)
        img = Image.open(BytesIO(bytes_thumbnail))

        thumbnail_checksum = str(imagehash.phash(img))
        assert thumbnail_checksum == phash

    @patch(
        "operationsgateway_api.src.config.Config.config.echo.url",
        config_echo_url,
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.echo.access_key",
        config_echo_access_key,
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.echo.secret_key",
        config_echo_secret_key,
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.echo.bucket_name",
        config_image_bucket_name,
    )
    @patch("boto3.resource")
    @patch(
        "operationsgateway_api.src.records.echo_interface.EchoInterface"
        ".upload_file_object",
    )
    def test_valid_upload_image(self, mock_upload_file_object, _):
        test_image = NullableImage(self.model)
        NullableImage.upload_image(test_image)

        assert mock_upload_file_object.call_count == 1

        assert len(mock_upload_file_object.call_args.args) == 2
        uploaded_bytes_io = mock_upload_file_object.call_args.args[0]
        assert isinstance(uploaded_bytes_io, BytesIO)
        assert (
            mock_upload_file_object.call_args.args[1] == f"nullable_images/{self.path}"
        )

    @patch(
        "operationsgateway_api.src.config.Config.config.echo.url",
        config_echo_url,
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.echo.access_key",
        config_echo_access_key,
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.echo.secret_key",
        config_echo_secret_key,
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.echo.bucket_name",
        config_image_bucket_name,
    )
    @patch("boto3.resource")
    @patch(
        "operationsgateway_api.src.records.echo_interface.EchoInterface.upload_file_object",
        side_effect=EchoS3Error("Mocked Exception"),
    )
    def test_invalid_upload_image(self, _, __):
        test_image = NullableImage(self.model)
        response = NullableImage.upload_image(test_image)
        assert response == "path"

    @pytest.mark.asyncio
    @patch(
        "operationsgateway_api.src.config.Config.config.echo.url",
        config_echo_url,
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.echo.access_key",
        config_echo_access_key,
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.echo.secret_key",
        config_echo_secret_key,
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.echo.bucket_name",
        config_image_bucket_name,
    )
    @patch("boto3.resource")
    async def test_valid_get_image(self, _):
        with patch(
            "operationsgateway_api.src.records.echo_interface.EchoInterface"
            ".download_file_object",
            return_value=BytesIO(self.stored_bytes),
        ):
            test_image = await NullableImage.get_image(
                record_id="test_record_id",
                channel_name="test_channel_name",
                colourmap_name="bwr",
            )

        phash = str(imagehash.phash(Image.open(BytesIO(test_image.getvalue()))))
        assert phash == "926e4ba649a6cc5e"

    @pytest.mark.asyncio
    @patch(
        "operationsgateway_api.src.config.Config.config.echo.url",
        config_echo_url,
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.echo.access_key",
        config_echo_access_key,
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.echo.secret_key",
        config_echo_secret_key,
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.echo.bucket_name",
        config_image_bucket_name,
    )
    @patch("boto3.resource")
    @patch(
        "operationsgateway_api.src.records.echo_interface.EchoInterface"
        ".download_file_object",
        side_effect=EchoS3Error("Mocked Exception"),
    )
    @pytest.mark.parametrize(
        "expected_exception, record_count",
        [
            pytest.param(ImageError, 1, id="Image cannot be found on object storage"),
            pytest.param(ImageNotFoundError, 0, id="Invalid record ID/channel name"),
            pytest.param(ImageError, 2, id="Unexpected error"),
        ],
    )
    async def test_invalid_get_image(self, _, __, expected_exception, record_count):
        with patch(
            "operationsgateway_api.src.mongo.interface.MongoDBInterface"
            ".count_documents",
            return_value=record_count,
        ):
            with pytest.raises(expected_exception):
                await NullableImage.get_image(
                    record_id="test_record_id",
                    channel_name="test_channel_name",
                    colourmap_name="bwr",
                )
