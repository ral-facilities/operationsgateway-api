import base64
from io import BytesIO
import os
from unittest.mock import patch

import imagehash
import numpy as np
from PIL import Image as PILImage
import pytest

from operationsgateway_api.src.exceptions import (
    EchoS3Error,
    ImageError,
    ImageNotFoundError,
)
from operationsgateway_api.src.models import ImageModel
from operationsgateway_api.src.records.image import Image


class MockImage:
    def __init__(self, mode, size):
        self.mode = mode
        self.size = size

    def thumbnail(self, size, resample=PILImage.BICUBIC):
        pass


class TestImage:
    config_echo_url = "https://mytesturl.com"
    config_echo_access_key = "TestAccessKey"
    config_echo_secret_key = "TestSecretKey"
    config_image_bucket_name = "MyTestBucket"
    test_image_path = "test/image/path.png"

    def _get_bytes_of_image(self, filename):
        print(f"PATH: {os.path.dirname(os.path.realpath(__file__))}")
        img = PILImage.open(f"{os.path.dirname(os.path.realpath(__file__))}/{filename}")
        b = BytesIO()
        img.save(b, "PNG")

        return b

    def test_init(self):
        test_image = Image(
            ImageModel(path="test/path/photo.png", data=np.ndarray(shape=(2, 2))),
        )
        assert isinstance(test_image.image, ImageModel)

    def test_create_thumbnail(self):
        test_image = Image(
            ImageModel(
                path="test/path/photo.png",
                data=np.ones(shape=(300, 300), dtype=np.int8),
            ),
        )
        test_image.create_thumbnail()

        bytes_thumbnail = base64.b64decode(test_image.thumbnail)
        img = PILImage.open(BytesIO(bytes_thumbnail))
        thumbnail_checksum = str(imagehash.phash(img))
        assert thumbnail_checksum == "0000000000000000"
        # the reason only 0s are being asserted is because this is checking the hash of
        # a purely black 300x300 square created in the test_image above

    def test_alternative_mode_thumbnail(self):
        test_image = Image(
            ImageModel(
                path="test/path/photo.png",
                data=np.ones(shape=(300, 300), dtype=np.int8),
            ),
        )

        with patch("PIL.Image.open", autospec=True) as mock_image_open:
            mock_img = MockImage(mode="RGB", size=(200, 150))
            mock_image_open.return_value = mock_img

            with pytest.raises(
                AttributeError,
                match="'MockImage' object has no attribute 'save'",
            ):
                test_image.create_thumbnail()

    @pytest.mark.parametrize(
        "image_path, expected_record_id, expected_channel_name",
        [
            pytest.param(
                "20220408165857/N_INP_NF_IMAGE.png",
                "20220408165857",
                "N_INP_NF_IMAGE",
                id="Typical path",
            ),
            pytest.param(
                "test/path.png",
                "test",
                "path",
                id="Test path",
            ),
            pytest.param(
                "/test/path.png",
                "test",
                "path",
                id="Path starting at root level",
            ),
        ],
    )
    def test_extract_metadata(
        self,
        image_path,
        expected_record_id,
        expected_channel_name,
    ):
        test_image = Image(
            ImageModel(path=image_path, data=np.ones(shape=(300, 300), dtype=np.int8)),
        )

        record_id, channel_name = test_image.extract_metadata_from_path()
        assert record_id == expected_record_id
        assert channel_name == expected_channel_name

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
        test_image = Image(
            ImageModel(
                path=self.test_image_path,
                data=np.ones(shape=(300, 300), dtype=np.int8),
            ),
        )
        Image.upload_image(test_image)

        assert mock_upload_file_object.call_count == 1

        assert len(mock_upload_file_object.call_args.args) == 2
        assert isinstance(mock_upload_file_object.call_args.args[0], BytesIO)
        assert (
            mock_upload_file_object.call_args.args[1]
            == f"images/{self.test_image_path}"
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
        "PIL.Image.fromarray",
        side_effect=TypeError("Mocked Exception"),
    )
    def test_invalid_upload_image(self, _, __):
        test_image = Image(
            ImageModel(
                path=self.test_image_path,
                data=np.ones(shape=(300, 300), dtype=np.int8),
            ),
        )
        with pytest.raises(ImageError):
            Image.upload_image(test_image)

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
    @pytest.mark.parametrize(
        "expected_image_filename, original_image_flag",
        [
            pytest.param("original_image.png", True, id="Get original greyscale image"),
            pytest.param("jet_image.png", False, id="Get false colour image"),
        ],
    )
    async def test_valid_get_image(
        self,
        _,
        expected_image_filename,
        original_image_flag,
    ):
        with patch(
            "operationsgateway_api.src.records.echo_interface.EchoInterface"
            ".download_file_object",
            return_value=self._get_bytes_of_image("original_image.png"),
        ):
            with patch(
                "operationsgateway_api.src.records.false_colour_handler"
                ".FalseColourHandler.apply_false_colour",
                return_value=self._get_bytes_of_image(expected_image_filename),
            ):
                test_image = await Image.get_image(
                    "test_record_id",
                    "test_channel_name",
                    original_image_flag,
                    0,
                    255,
                    "jet",
                )

            assert (
                test_image.getvalue()
                == self._get_bytes_of_image(expected_image_filename).getvalue()
            )

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
                await Image.get_image(
                    "test_record_id",
                    "test_channel_name",
                    True,
                    0,
                    255,
                    "jet",
                )

    def test_get_relative_path(self):
        test_path = Image.get_relative_path("20220408165857", "N_INP_NF_IMAGE")
        assert test_path == "20220408165857/N_INP_NF_IMAGE.png"
