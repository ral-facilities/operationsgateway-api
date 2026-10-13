from io import BytesIO
from unittest.mock import AsyncMock, patch

import numpy as np
from PIL import Image as PILImage
import pytest

from operationsgateway_api.src.exceptions import (
    MissingAttributeError,
    QueryParameterError,
    RecordError,
)
from operationsgateway_api.src.models import (
    ChannelDtype,
    ImageModel,
    PartialImageSeriesChannelMetadataModel,
    PartialImageSeriesChannelModel,
    PartialRecordModel,
    PartialScalarChannelModel,
)
from operationsgateway_api.src.records.image import Image
from operationsgateway_api.src.records.image_series import ImageSeries
from test.conftest import IMAGE_SERIES_FRAMES

RECORD_ID = "20200407142816000"
CHANNEL_NAME = "TEST_IMAGE_SERIES"
IMAGE_PATH = f"{RECORD_ID}/{CHANNEL_NAME}.npy"

# The same frames `create_test_hdf_file` writes, so the unit tests and the
# endpoint tests are exercising identical data.
FRAMES = np.array(IMAGE_SERIES_FRAMES, dtype=np.uint16)
STORAGE_DTYPE = ImageSeries.get_storage_dtype(16)


def build_series(data: np.ndarray = FRAMES) -> ImageSeries:
    return ImageSeries(ImageModel(path=IMAGE_PATH, data=data, bit_depth=16))


def build_channel(
    shape: tuple | None = FRAMES.shape,
    header_offset_bytes: int | None = 128,
    image_path: str | None = IMAGE_PATH,
    channel_dtype=ChannelDtype.IMAGE_SERIES,
    bit_depth: int | None = 16,
) -> PartialImageSeriesChannelModel:
    return PartialImageSeriesChannelModel(
        metadata=PartialImageSeriesChannelMetadataModel(
            channel_dtype=channel_dtype,
            bit_depth=bit_depth,
        ),
        image_path=image_path,
        shape=shape,
        header_offset_bytes=header_offset_bytes,
    )


def patch_record(channel) -> patch:
    """Patch the record lookup `get_frame` performs, returning `channel`."""
    channels = {CHANNEL_NAME: channel} if channel is not None else {}
    return patch(
        "operationsgateway_api.src.records.image_series.Record.find_record_by_id",
        AsyncMock(return_value=PartialRecordModel(_id=RECORD_ID, channels=channels)),
    )


async def store_and_get_frame(
    data: np.ndarray,
    bit_depth: int,
    frame_index: int,
) -> bytes:
    """
    Store `data` as a series then read one frame back, with Echo replaced by an
    in memory copy of the uploaded object that serves byte range requests.
    """
    series = ImageSeries(ImageModel(path=IMAGE_PATH, data=data, bit_depth=bit_depth))
    uploaded = BytesIO()

    async def capture(file_object: BytesIO, _path: str) -> None:
        uploaded.write(file_object.getvalue())

    async def serve_range(object_path, start_byte, end_byte) -> bytes:
        return uploaded.getvalue()[start_byte : end_byte + 1]

    with patch(
        "operationsgateway_api.src.records.image_series.get_echo_interface",
    ) as get_echo:
        get_echo.return_value.upload_file_object = AsyncMock(side_effect=capture)
        assert await ImageSeries.upload_image(series) is None

        channel = build_channel(
            shape=data.shape,
            bit_depth=bit_depth,
            header_offset_bytes=ImageSeries.get_header_offset_bytes(
                data.shape,
                ImageSeries.get_storage_dtype(bit_depth),
            ),
        )
        get_echo.return_value.download_file_range = AsyncMock(side_effect=serve_range)
        with patch_record(channel):
            return await ImageSeries.get_frame(RECORD_ID, CHANNEL_NAME, frame_index)


class TestImageSeriesHeader:
    def test_header_is_readable_by_numpy(self):
        """
        The header written before the pixel data must be a valid NPY header
        describing the full series, so the stored object can be read back with
        numpy as well as by byte range.
        """
        buffer = BytesIO()
        ImageSeries.write_npy_header(buffer, FRAMES.shape, STORAGE_DTYPE)
        buffer.write(
            np.ascontiguousarray(FRAMES, dtype=STORAGE_DTYPE).data.cast("B"),
        )
        buffer.seek(0)

        np.testing.assert_array_equal(np.load(buffer), FRAMES)

    def test_header_offset_matches_header_length(self):
        """
        `get_header_offset_bytes` is what every frame's byte range is measured
        from, so it has to equal the real length of the header.
        """
        buffer = BytesIO()
        ImageSeries.write_npy_header(buffer, FRAMES.shape, STORAGE_DTYPE)

        offset = ImageSeries.get_header_offset_bytes(FRAMES.shape, STORAGE_DTYPE)
        assert offset == buffer.tell()


class TestImageSeriesGetFrame:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("frame_index", [0, 1, 2])
    async def test_requests_correct_byte_range(self, frame_index: int):
        """
        Each frame is a fixed-size slice after the header. Getting this arithmetic
        wrong returns a silently incorrect frame rather than an error, so the exact
        range requested is asserted.
        """
        header_offset = 128
        frame_size = 2 * 2 * STORAGE_DTYPE.itemsize
        frame_bytes = np.ascontiguousarray(
            FRAMES[frame_index],
            dtype=STORAGE_DTYPE,
        ).tobytes()

        download = AsyncMock(return_value=frame_bytes)
        with patch_record(build_channel(header_offset_bytes=header_offset)), patch(
            "operationsgateway_api.src.records.image_series.get_echo_interface",
        ) as get_echo:
            get_echo.return_value.download_file_range = download
            png = await ImageSeries.get_frame(RECORD_ID, CHANNEL_NAME, frame_index)

        expected_start = header_offset + frame_index * frame_size
        download.assert_awaited_once_with(
            object_path=ImageSeries.get_full_path(IMAGE_PATH),
            start_byte=expected_start,
            end_byte=expected_start + frame_size - 1,
        )

        # The PNG returned should contain exactly the requested frame.
        with PILImage.open(BytesIO(png)) as image:
            np.testing.assert_array_equal(np.array(image), FRAMES[frame_index])

    @pytest.mark.asyncio
    async def test_missing_channel(self):
        with patch_record(None):
            with pytest.raises(MissingAttributeError):
                await ImageSeries.get_frame(RECORD_ID, CHANNEL_NAME, 0)

    @pytest.mark.asyncio
    async def test_channel_is_not_an_image_series(self):
        with patch_record(PartialScalarChannelModel(data=1)):
            with pytest.raises(QueryParameterError):
                await ImageSeries.get_frame(RECORD_ID, CHANNEL_NAME, 0)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "kwargs",
        [
            pytest.param({"shape": None}, id="no shape"),
            pytest.param({"shape": (3, 0, 2)}, id="zero dimension"),
            pytest.param({"header_offset_bytes": None}, id="no header offset"),
            pytest.param({"header_offset_bytes": 0}, id="zero header offset"),
            pytest.param({"image_path": None}, id="no image path"),
            pytest.param({"bit_depth": None}, id="no bit depth"),
        ],
    )
    async def test_invalid_storage_metadata(self, kwargs: dict):
        """Without valid storage metadata the byte range cannot be calculated."""
        with patch_record(build_channel(**kwargs)):
            with pytest.raises(RecordError):
                await ImageSeries.get_frame(RECORD_ID, CHANNEL_NAME, 0)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("frame_index", [3, 99])
    async def test_frame_index_out_of_range(self, frame_index: int):
        with patch_record(build_channel()):
            with pytest.raises(QueryParameterError):
                await ImageSeries.get_frame(RECORD_ID, CHANNEL_NAME, frame_index)


class TestImageSeriesRoundTrip:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("frame_index", [0, 1, 2])
    async def test_upload_then_get_frame(self, frame_index: int):
        """
        Upload a series and read each frame back out, to check the header offset
        and frame stride agree with each other end to end. A mismatch here would
        return a shifted frame, which the two halves tested in isolation cannot
        catch.
        """
        png = await store_and_get_frame(FRAMES, 16, frame_index)

        with PILImage.open(BytesIO(png)) as image:
            np.testing.assert_array_equal(np.array(image), FRAMES[frame_index])

    @pytest.mark.asyncio
    async def test_missing_channel(self):
        with patch_record(None):
            with pytest.raises(MissingAttributeError):
                await ImageSeries.get_frame(RECORD_ID, CHANNEL_NAME, 0)

    @pytest.mark.asyncio
    async def test_channel_is_not_an_image_series(self):
        with patch_record(PartialScalarChannelModel(data=1)):
            with pytest.raises(QueryParameterError):
                await ImageSeries.get_frame(RECORD_ID, CHANNEL_NAME, 0)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "kwargs",
        [
            pytest.param({"shape": None}, id="no shape"),
            pytest.param({"shape": (3, 0, 2)}, id="zero dimension"),
            pytest.param({"header_offset_bytes": None}, id="no header offset"),
            pytest.param({"header_offset_bytes": 0}, id="zero header offset"),
            pytest.param({"image_path": None}, id="no image path"),
            pytest.param({"bit_depth": None}, id="no bit depth"),
        ],
    )
    async def test_invalid_storage_metadata(self, kwargs: dict):
        """Without valid storage metadata the byte range cannot be calculated."""
        with patch_record(build_channel(**kwargs)):
            with pytest.raises(RecordError):
                await ImageSeries.get_frame(RECORD_ID, CHANNEL_NAME, 0)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("frame_index", [3, 99])
    async def test_frame_index_out_of_range(self, frame_index: int):
        with patch_record(build_channel()):
            with pytest.raises(QueryParameterError):
                await ImageSeries.get_frame(RECORD_ID, CHANNEL_NAME, frame_index)


class TestImageSeriesRoundTrip:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("frame_index", [0, 1, 2])
    async def test_upload_then_get_frame(self, frame_index: int):
        """
        Upload a series and read each frame back out, to check the header offset
        and frame stride agree with each other end to end. A mismatch here would
        return a shifted frame, which the two halves tested in isolation cannot
        catch.
        """
        series = build_series()
        uploaded = BytesIO()

        async def capture(file_object: BytesIO, _path: str) -> None:
            uploaded.write(file_object.getvalue())

        async def serve_range(object_path, start_byte, end_byte) -> bytes:
            return uploaded.getvalue()[start_byte : end_byte + 1]

        with patch(
            "operationsgateway_api.src.records.image_series.get_echo_interface",
        ) as get_echo:
            get_echo.return_value.upload_file_object = AsyncMock(side_effect=capture)
            assert await ImageSeries.upload_image(series) is None

            channel = build_channel(
                header_offset_bytes=ImageSeries.get_header_offset_bytes(
                    FRAMES.shape,
                    STORAGE_DTYPE,
                ),
            )
            get_echo.return_value.download_file_range = AsyncMock(
                side_effect=serve_range,
            )
            with patch_record(channel):
                png = await ImageSeries.get_frame(
                    RECORD_ID,
                    CHANNEL_NAME,
                    frame_index,
                )

        with PILImage.open(BytesIO(png)) as image:
            np.testing.assert_array_equal(np.array(image), FRAMES[frame_index])


# Pixel values chosen to reach full scale for their bit depth, as that is where
# storing them at the wrong scale is most visible.
EIGHT_BIT = np.array([[[0, 64], [128, 255]], [[255, 128], [64, 0]]], dtype=np.uint8)
TWELVE_BIT = np.array(
    [[[0, 1024], [2048, 4095]], [[4095, 2048], [1024, 0]]],
    dtype=np.uint16,
)

BIT_DEPTH_CASES = [
    pytest.param(EIGHT_BIT, 8, np.uint8, "L", id="8 bit"),
    pytest.param(TWELVE_BIT, 12, np.uint16, "I;16", id="12 bit"),
    pytest.param(FRAMES, 16, np.uint16, "I;16", id="16 bit"),
]


class TestImageSeriesBitDepth:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("data", "bit_depth", "expected_dtype", "expected_mode"),
        BIT_DEPTH_CASES,
    )
    @pytest.mark.parametrize("frame_index", [0, 1])
    async def test_frames_keep_their_brightness(
        self,
        data: np.ndarray,
        bit_depth: int,
        expected_dtype: type,
        expected_mode: str,
        frame_index: int,
    ):
        """
        A series is stored at 8 or 16 bit like a normal image, with other depths
        shifted into the most significant bits. That keeps a full scale pixel full
        scale: an 8 bit 255 must come back as 255 in an 8 bit PNG, not as 255 in a
        16 bit PNG where it would be about 0.4% of full scale and look black.
        """
        if frame_index >= len(data):
            pytest.skip("series has fewer frames")

        png = await store_and_get_frame(data, bit_depth, frame_index)

        target_bits = 8 if bit_depth <= 8 else 16
        expected = data[frame_index].astype(expected_dtype) * 2 ** (
            target_bits - bit_depth
        )
        with PILImage.open(BytesIO(png)) as image:
            assert image.mode == expected_mode
            np.testing.assert_array_equal(np.array(image), expected)

        # As for normal images, the original bit depth is recorded in the PNG
        assert png[png.find(b"sBIT") + 4] == bit_depth

    @pytest.mark.parametrize(
        ("data", "bit_depth", "expected_dtype", "expected_mode"),
        BIT_DEPTH_CASES,
    )
    def test_thumbnail_matches_normal_image(
        self,
        data: np.ndarray,
        bit_depth: int,
        expected_dtype: type,
        expected_mode: str,
    ):
        """
        A series thumbnail comes out the same as that of a normal image of the same
        bit depth, as both are made by the same code from already normalised data.
        """
        series = ImageSeries(
            ImageModel(path=IMAGE_PATH, data=data.copy(), bit_depth=bit_depth),
        )
        series.create_thumbnail()

        image = Image(
            ImageModel(path=IMAGE_PATH, data=data[0].copy(), bit_depth=bit_depth),
        )
        image.create_thumbnail()

        assert series.thumbnail == image.thumbnail
