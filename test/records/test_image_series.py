from unittest.mock import AsyncMock, patch

import pytest

from operationsgateway_api.src.exceptions import (
    MissingAttributeError,
    QueryParameterError,
    RecordError,
)
from operationsgateway_api.src.models import (
    ChannelDtype,
    PartialImageSeriesChannelMetadataModel,
    PartialImageSeriesChannelModel,
    PartialRecordModel,
    PartialScalarChannelModel,
)
from operationsgateway_api.src.records.image_series import ImageSeries
from test.conftest import IMAGE_SERIES_CHANNEL_NAME, RECORD_ID_TMP


class TestImageSeriesGetFrame:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("channels", "frame_index", "expected_error"),
        [
            # The record has no channel with this name, so there is nothing to read.
            pytest.param({}, 0, MissingAttributeError, id="missing channel"),
            # The channel exists but is a scalar, not an image series.
            pytest.param(
                {IMAGE_SERIES_CHANNEL_NAME: PartialScalarChannelModel(data=1)},
                0,
                QueryParameterError,
                id="channel is not an image series",
            ),
            # The channel has series fields but its metadata says it is a normal image.
            pytest.param(
                {
                    IMAGE_SERIES_CHANNEL_NAME: PartialImageSeriesChannelModel(
                        metadata=PartialImageSeriesChannelMetadataModel(
                            channel_dtype=ChannelDtype.IMAGE,
                            bit_depth=16,
                        ),
                        image_path="image_series/series.npy",
                        shape=(3, 2, 2),
                        header_offset_bytes=128,
                    ),
                },
                0,
                RecordError,
                id="metadata does not say image_series",
            ),
            # Without the shape the size of one frame cannot be worked out.
            pytest.param(
                {
                    IMAGE_SERIES_CHANNEL_NAME: PartialImageSeriesChannelModel(
                        metadata=PartialImageSeriesChannelMetadataModel(
                            channel_dtype=ChannelDtype.IMAGE_SERIES,
                            bit_depth=16,
                        ),
                        image_path="image_series/series.npy",
                        shape=None,
                        header_offset_bytes=128,
                    ),
                },
                0,
                RecordError,
                id="no shape",
            ),
            # A dimension of zero would make a frame with no pixels.
            pytest.param(
                {
                    IMAGE_SERIES_CHANNEL_NAME: PartialImageSeriesChannelModel(
                        metadata=PartialImageSeriesChannelMetadataModel(
                            channel_dtype=ChannelDtype.IMAGE_SERIES,
                            bit_depth=16,
                        ),
                        image_path="image_series/series.npy",
                        shape=(3, 0, 2),
                        header_offset_bytes=128,
                    ),
                },
                0,
                RecordError,
                id="zero dimension",
            ),
            # Without the header offset the start of the pixel data is unknown.
            pytest.param(
                {
                    IMAGE_SERIES_CHANNEL_NAME: PartialImageSeriesChannelModel(
                        metadata=PartialImageSeriesChannelMetadataModel(
                            channel_dtype=ChannelDtype.IMAGE_SERIES,
                            bit_depth=16,
                        ),
                        image_path="image_series/series.npy",
                        shape=(3, 2, 2),
                        header_offset_bytes=None,
                    ),
                },
                0,
                RecordError,
                id="no header offset",
            ),
            # An offset of zero cannot be right, as the NPY header always comes first.
            pytest.param(
                {
                    IMAGE_SERIES_CHANNEL_NAME: PartialImageSeriesChannelModel(
                        metadata=PartialImageSeriesChannelMetadataModel(
                            channel_dtype=ChannelDtype.IMAGE_SERIES,
                            bit_depth=16,
                        ),
                        image_path="image_series/series.npy",
                        shape=(3, 2, 2),
                        header_offset_bytes=0,
                    ),
                },
                0,
                RecordError,
                id="zero header offset",
            ),
            # Without the image path there is no object to read from Echo.
            pytest.param(
                {
                    IMAGE_SERIES_CHANNEL_NAME: PartialImageSeriesChannelModel(
                        metadata=PartialImageSeriesChannelMetadataModel(
                            channel_dtype=ChannelDtype.IMAGE_SERIES,
                            bit_depth=16,
                        ),
                        image_path=None,
                        shape=(3, 2, 2),
                        header_offset_bytes=128,
                    ),
                },
                0,
                RecordError,
                id="no image path",
            ),
            # Without the bit depth the number of bytes per pixel is unknown.
            pytest.param(
                {
                    IMAGE_SERIES_CHANNEL_NAME: PartialImageSeriesChannelModel(
                        metadata=PartialImageSeriesChannelMetadataModel(
                            channel_dtype=ChannelDtype.IMAGE_SERIES,
                            bit_depth=None,
                        ),
                        image_path="image_series/series.npy",
                        shape=(3, 2, 2),
                        header_offset_bytes=128,
                    ),
                },
                0,
                RecordError,
                id="no bit depth",
            ),
            # The series has 3 frames, so the last valid index is 2.
            pytest.param(
                {
                    IMAGE_SERIES_CHANNEL_NAME: PartialImageSeriesChannelModel(
                        metadata=PartialImageSeriesChannelMetadataModel(
                            channel_dtype=ChannelDtype.IMAGE_SERIES,
                            bit_depth=16,
                        ),
                        image_path="image_series/series.npy",
                        shape=(3, 2, 2),
                        header_offset_bytes=128,
                    ),
                },
                3,
                QueryParameterError,
                id="frame index is one past the last frame",
            ),
            # Frames count from zero, so a negative index is never valid.
            pytest.param(
                {
                    IMAGE_SERIES_CHANNEL_NAME: PartialImageSeriesChannelModel(
                        metadata=PartialImageSeriesChannelMetadataModel(
                            channel_dtype=ChannelDtype.IMAGE_SERIES,
                            bit_depth=16,
                        ),
                        image_path="image_series/series.npy",
                        shape=(3, 2, 2),
                        header_offset_bytes=128,
                    ),
                },
                -1,
                QueryParameterError,
                id="frame index is negative",
            ),
        ],
    )
    async def test_get_frame_errors(
        self,
        channels: dict,
        frame_index: int,
        expected_error: type[Exception],
    ):
        record = PartialRecordModel(_id=RECORD_ID_TMP, channels=channels)

        with patch(
            "operationsgateway_api.src.records.image_series.Record.find_record_by_id",
            AsyncMock(return_value=record),
        ):
            with pytest.raises(expected_error):
                await ImageSeries.get_frame(
                    RECORD_ID_TMP,
                    IMAGE_SERIES_CHANNEL_NAME,
                    frame_index,
                )
