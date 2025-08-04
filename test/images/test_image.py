import base64
from io import BytesIO
import logging
import os
from unittest.mock import patch

import imagehash
import numpy as np
from PIL import Image as PILImage
from pydantic import SecretStr
import pytest

from operationsgateway_api.src.exceptions import (
    EchoS3Error,
    ImageError,
    ImageNotFoundError,
)
from operationsgateway_api.src.models import ImageModel
from operationsgateway_api.src.records.image import Image
from test.conftest import clear_lru_cache
from test.records.conftest import remove_test_objects


class MockImage:
    def __init__(self, mode, size):
        self.mode = mode
        self.size = size

    def thumbnail(self, size, resample=PILImage.BICUBIC):
        pass


class TestImage:
    config_echo_url = "https://mytesturl.com"
    config_echo_access_key = SecretStr("TestAccessKey")
    config_echo_secret_key = SecretStr("TestSecretKey")
    config_image_bucket_name = "MyTestBucket"

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
                data=np.ones(shape=(300, 300), dtype=np.uint8),
            ),
        )
        test_image.create_thumbnail()

        bytes_thumbnail = base64.b64decode(test_image.thumbnail)
        img = PILImage.open(BytesIO(bytes_thumbnail))
        thumbnail_checksum = str(imagehash.phash(img))
        assert thumbnail_checksum == "8000000000000000"

    @pytest.mark.parametrize(
        # image_size parameter = (rows, columns), not (width, height) which is what
        # the other parameters in this test use. image_size is the shape of the numpy
        # array. See https://data-flair.training/blogs/numpy-broadcasting/ for a good
        # illustration
        "image_size, config_thumbnail_size, expected_thumbnail_size",
        [
            pytest.param((300, 300), (50, 50), (50, 50), id="50x50 thumbnail"),
            # (400, 300) makes a portrait image, as per numpy array shape (see above
            # comment)
            pytest.param(
                (400, 300),
                (60, 80),
                (60, 80),
                id="60x80 thumbnail (portrait)",
            ),
            pytest.param(
                (300, 400),
                (60, 80),
                (60, 45),
                id="60x45 thumbnail (landscape)",
            ),
            pytest.param(
                (300, 300),
                (75, 100),
                (75, 75),
                id="75x75 thumbnail (square image)",
            ),
        ],
    )
    def test_create_thumbnail_config_size(
        self,
        image_size,
        config_thumbnail_size,
        expected_thumbnail_size,
    ):
        test_image = Image(
            ImageModel(
                path="test/path/photo.png",
                data=np.ones(shape=image_size, dtype=np.uint8),
            ),
        )
        with patch(
            "operationsgateway_api.src.config.Config.config.images.thumbnail_size",
            config_thumbnail_size,
        ):
            test_image.create_thumbnail()

        bytes_thumbnail = base64.b64decode(test_image.thumbnail)
        img = PILImage.open(BytesIO(bytes_thumbnail))
        assert img.size == expected_thumbnail_size

    def test_alternative_mode_thumbnail(self):
        test_image = Image(
            ImageModel(
                path="test/path/photo.png",
                data=np.ones(shape=(300, 300), dtype=np.uint8),
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
        ["image_path", "expected_channel_name"],
        [
            pytest.param(
                "20220408165857/N_INP_NF_IMAGE.png",
                "N_INP_NF_IMAGE",
                id="Typical path",
            ),
            pytest.param(
                "test/path.png",
                "path",
                id="Test path",
            ),
            pytest.param(
                "/test/path.png",
                "path",
                id="Path starting at root level",
            ),
        ],
    )
    def test_extract_metadata(
        self,
        image_path,
        expected_channel_name,
    ):
        test_image = Image(
            ImageModel(path=image_path, data=np.ones(shape=(300, 300), dtype=np.uint8)),
        )

        channel_name = test_image.get_channel_name_from_path()
        assert channel_name == expected_channel_name

    @pytest.mark.parametrize(["bit_depth"], [pytest.param(None), pytest.param(8)])
    @pytest.mark.parametrize(
        ["path"],
        [
            pytest.param("1952/06/05/070023/test-channel-name.png"),
            pytest.param("19520605070023/test-channel-name.png"),
        ],
    )
    @pytest.mark.asyncio
    async def test_valid_upload_image(
        self,
        bit_depth: int,
        path: str,
        remove_test_objects: None,
        clear_lru_cache: None,
    ):
        test_image = Image(
            ImageModel(
                path=path,
                data=np.ones(shape=(300, 300), dtype=np.uint8),
                bit_depth=bit_depth,
            ),
        )
        response = await Image.upload_image(test_image)

        assert response is None

        bytes_io = await Image.get_image(
            record_id="19520605070023",
            channel_name="test-channel-name",
            original_image=True,
            lower_level=0,
            upper_level=255,
            limit_bit_depth=8,
            colourmap_name=None,
        )
        assert isinstance(bytes_io, BytesIO)

        uploaded_bytes = bytes_io.getvalue()
        s_bit_offset = uploaded_bytes.find(b"sBIT")
        if bit_depth is None:
            assert s_bit_offset == -1, uploaded_bytes[: s_bit_offset + 10]
        else:
            assert s_bit_offset != -1
            s_bit = uploaded_bytes[s_bit_offset + 4 : s_bit_offset + 5]
            assert int.from_bytes(s_bit, byteorder="big") == bit_depth

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
        "PIL.Image.fromarray",
        side_effect=TypeError("Mocked Exception"),
    )
    async def test_invalid_upload_image(self, _, __):
        test_image = Image(
            ImageModel(
                path="test/image/path.png",
                data=np.ones(shape=(300, 300), dtype=np.uint8),
            ),
        )
        with pytest.raises(ImageError):
            await Image.upload_image(test_image)

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
                    record_id="test_record_id",
                    channel_name="test_channel_name",
                    original_image=original_image_flag,
                    lower_level=0,
                    upper_level=255,
                    limit_bit_depth=8,
                    colourmap_name="jet",
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
                    record_id="test_record_id",
                    channel_name="test_channel_name",
                    original_image=True,
                    lower_level=0,
                    upper_level=255,
                    limit_bit_depth=8,
                    colourmap_name="jet",
                )

    @pytest.mark.parametrize(
        ["use_subdirectories", "path"],
        [
            pytest.param(False, "20220408165857/N_INP_NF_IMAGE.png"),
            pytest.param(True, "2022/04/08/165857/N_INP_NF_IMAGE.png"),
        ],
    )
    def test_get_relative_path(self, use_subdirectories: bool, path: str):
        test_path = Image.get_relative_path(
            "20220408165857",
            "N_INP_NF_IMAGE",
            use_subdirectories=use_subdirectories,
        )
        assert test_path == path

    @pytest.mark.parametrize(
        ["data", "bit_depth", "record_tuples", "dtype", "value"],
        [
            pytest.param(
                np.ones(1, np.uint8) * 255,
                0,
                [],
                np.uint8,
                0,
                id="Expect to shift up by 8 bits, 1111 1111 -> 0000 0000",
            ),
            pytest.param(
                np.ones(1, np.uint16) * 65535,
                0,
                [
                    (
                        "root",
                        logging.WARNING,
                        (
                            "Specified bit depth is lower than actual bit depth with "
                            "dtype of uint16, only data in the 0 least significant "
                            "bits will be kept"
                        ),
                    ),
                ],
                np.uint8,
                0,
                id=(
                    "Expect to shift up by 8 bits, 1111 1111 1111 1111 -> 0000 0000, "
                    "and warn only lower bits are kept"
                ),
            ),
            pytest.param(
                np.ones(1, np.uint8) * 255,
                6,
                [],
                np.uint8,
                252,
                id="Expect to shift up by 2 bits, 1111 1111 -> 1111 1100",
            ),
            pytest.param(
                np.ones(1, np.uint16) * 65535,
                6,
                [
                    (
                        "root",
                        logging.WARNING,
                        (
                            "Specified bit depth is lower than actual bit depth with "
                            "dtype of uint16, only data in the 6 least significant "
                            "bits will be kept"
                        ),
                    ),
                ],
                np.uint8,
                252,
                id=(
                    "Expect to shift up by 2 bits, 1111 1111 1111 1111 -> 1111 1100, "
                    "and warn only lower bits are kept"
                ),
            ),
            pytest.param(
                np.ones(1, np.uint8) * 255,
                8,
                [],
                np.uint8,
                255,
                id="Expect no change",
            ),
            pytest.param(
                np.ones(1, np.uint16) * 255,
                8,
                [
                    (
                        "root",
                        logging.WARNING,
                        (
                            "Specified bit depth is lower than actual bit depth with "
                            "dtype of uint16, only data in the 8 least significant "
                            "bits will be kept"
                        ),
                    ),
                ],
                np.uint8,
                255,
                id="Expect no change, and warn that only lower bits are kept",
            ),
            pytest.param(
                np.ones(1, np.uint8) * 255,
                12,
                [],
                np.uint16,
                4080,
                id="Expect to shift up 4 bits, 1111 1111 -> 0000 1111 1111 0000",
            ),
            pytest.param(
                np.ones(1, np.uint16) * 65535,
                12,
                [],
                np.uint16,
                65520,
                id=(
                    "Expect to shift up by 4 bits, "
                    "1111 1111 1111 1111 -> 1111 1111 1111 0000"
                ),
            ),
            pytest.param(
                np.ones(1, np.uint8) * 255,
                16,
                [],
                np.uint16,
                255,
                id="Expect no change",
            ),
            pytest.param(
                np.ones(1, np.uint16) * 65535,
                16,
                [],
                np.uint16,
                65535,
                id="Expect no change",
            ),
            pytest.param(
                np.ones(1, np.uint8) * 255,
                24,
                [
                    (
                        "root",
                        logging.WARNING,
                        (
                            "Specified bit depth is higher than the max supported "
                            "depth of 16, only data in the 16 most significant bits "
                            "will be kept"
                        ),
                    ),
                ],
                np.uint16,
                0,
                id=(
                    "Expect to shift down by 8 bits, 1111 1111 -> 0000 0000, "
                    "and warn only upper bits are kept"
                ),
            ),
            pytest.param(
                np.ones(1, np.uint16) * 65535,
                24,
                [
                    (
                        "root",
                        logging.WARNING,
                        (
                            "Specified bit depth is higher than the max supported "
                            "depth of 16, only data in the 16 most significant bits "
                            "will be kept"
                        ),
                    ),
                ],
                np.uint16,
                255,
                id=(
                    "Expect to shift down by 8 bits, 1111 1111 1111 1111 -> "
                    "0000 0000 1111 1111, and warn only upper bits are kept"
                ),
            ),
        ],
    )
    def test_bit_depth(
        self,
        data: np.ndarray,
        bit_depth: int,
        record_tuples: "list[tuple[str, int, str]]",
        dtype: type,
        value: int,
        caplog,
    ):
        image_model = ImageModel(path="", data=data, bit_depth=bit_depth)
        image = Image(image_model)
        assert caplog.record_tuples == record_tuples
        assert image.image.data.dtype == dtype
        assert image.image.data[0] == value
