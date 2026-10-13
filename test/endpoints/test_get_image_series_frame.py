import io
import json
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
import numpy as np
from PIL import Image
import pytest

from operationsgateway_api.src.records.image import Image as OGImage
from operationsgateway_api.src.records.image_series import ImageSeries
from operationsgateway_api.src.records.record import Record
from operationsgateway_api.src.routes.image_series import get_frame_array
from test.conftest import (
    IMAGE_SERIES_FRAMES,
    RECORD_ID_05_0800,
    RECORD_ID_TMP,
    set_preferred_colourmap,
    unset_preferred_colourmap,
)
from test.records.ingestion.create_test_hdf import create_test_hdf_file

CHANNEL_NAME = "TEST_IMAGE_SERIES"
EXPECTED_FRAMES = IMAGE_SERIES_FRAMES

# What the false colour parameters default to for a normal image too
DEFAULT_FALSE_COLOUR = {
    "colourmap_name": "viridis",
    "lower_level": 0,
    "upper_level": 255,
    "limit_bit_depth": 8,
}


async def ingest_image_series(test_app: TestClient, auth_token: str) -> None:
    """Submit the test HDF file so RECORD_ID_TMP has an image series channel."""
    await create_test_hdf_file()
    with open("test.h5", "rb") as file:
        response = test_app.post(
            "/submit/hdf",
            headers={"Authorization": f"Bearer {auth_token}"},
            files={"file": ("test.h5", file)},
        )
    assert response.status_code == 201, response.text


def frame_url(record_id: str, channel_name: str, frame_index: int) -> str:
    return f"/image-series/{record_id}/{channel_name}/frames/{frame_index}"


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def get_frame(
    test_app: TestClient,
    token: str,
    frame_index: int = 0,
    **params,
) -> bytes:
    """Get a frame of the ingested series, returning the bytes of the PNG."""
    response = test_app.get(
        frame_url(RECORD_ID_TMP, CHANNEL_NAME, frame_index),
        params=params,
        headers=auth(token),
    )
    assert response.status_code == 200, response.text
    return response.content


def as_array(png_bytes: bytes) -> np.ndarray:
    with Image.open(io.BytesIO(png_bytes)) as image:
        return np.array(image)


class TestGetImageSeriesFrame:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("frame_index", [0, 1, 2])
    async def test_get_frame_success(
        self,
        reset_record_storage,
        test_app: TestClient,
        login_and_get_token,
        frame_index: int,
    ):
        """Each frame should come back as the PNG of that frame, in order."""
        await ingest_image_series(test_app, login_and_get_token)

        response = test_app.get(
            frame_url(RECORD_ID_TMP, CHANNEL_NAME, frame_index),
            params={"original_image": True},
            headers=auth(login_and_get_token),
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"

        np.testing.assert_array_equal(
            as_array(response.content),
            np.array(EXPECTED_FRAMES[frame_index], dtype=np.uint16),
        )

    @pytest.mark.asyncio
    async def test_frames_are_distinct(
        self,
        reset_record_storage,
        test_app: TestClient,
        login_and_get_token,
    ):
        """
        Guards against every index returning the same frame, which byte-range
        arithmetic errors can cause while each request still succeeds.
        """
        await ingest_image_series(test_app, login_and_get_token)

        contents = {
            get_frame(test_app, login_and_get_token, frame_index, original_image=True)
            for frame_index in range(len(EXPECTED_FRAMES))
        }

        assert len(contents) == len(EXPECTED_FRAMES)

    @pytest.mark.asyncio
    async def test_frame_index_out_of_range(
        self,
        reset_record_storage,
        test_app: TestClient,
        login_and_get_token,
    ):
        await ingest_image_series(test_app, login_and_get_token)

        response = test_app.get(
            frame_url(RECORD_ID_TMP, CHANNEL_NAME, len(EXPECTED_FRAMES)),
            headers=auth(login_and_get_token),
        )

        assert response.status_code == 400

    def test_negative_frame_index_rejected(
        self,
        test_app: TestClient,
        login_and_get_token,
    ):
        """`frame_index` is declared as non negative, so this fails validation."""
        response = test_app.get(
            frame_url(RECORD_ID_05_0800, CHANNEL_NAME, -1),
            headers=auth(login_and_get_token),
        )

        assert response.status_code == 422

    def test_channel_is_not_an_image_series(
        self,
        test_app: TestClient,
        login_and_get_token,
    ):
        """An existing channel of the wrong type should be rejected, not served."""
        response = test_app.get(
            frame_url(RECORD_ID_05_0800, "FE-204-PSO-EM", 0),
            headers=auth(login_and_get_token),
        )

        assert response.status_code == 400

    def test_unknown_channel(self, test_app: TestClient, login_and_get_token):
        response = test_app.get(
            frame_url(RECORD_ID_05_0800, "NOT_A_CHANNEL", 0),
            headers=auth(login_and_get_token),
        )

        assert response.status_code == 404

    def test_unauthorised(self, test_app: TestClient):
        response = test_app.get(frame_url(RECORD_ID_05_0800, CHANNEL_NAME, 0))

        assert response.status_code == 401


class TestGetImageSeriesFrameFalseColour:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "params",
        [
            pytest.param({"colourmap_name": "coolwarm"}, id="colourmap"),
            pytest.param(
                {"lower_level": 1000, "upper_level": 40000, "limit_bit_depth": 16},
                id="lower and upper levels",
            ),
        ],
    )
    async def test_false_colour_parameters_are_applied(
        self,
        reset_record_storage,
        test_app: TestClient,
        login_and_get_token,
        params: dict,
    ):
        """
        The parameters should have the same effect on a frame as on a normal image,
        which is checked by applying false colour to the original frame directly.
        """
        await ingest_image_series(test_app, login_and_get_token)
        original = get_frame(test_app, login_and_get_token, 1, original_image=True)
        expected_parameters = {**DEFAULT_FALSE_COLOUR, **params}

        result = get_frame(
            test_app,
            login_and_get_token,
            1,
            **{"colourmap_name": "viridis", **params},
        )

        np.testing.assert_array_equal(
            as_array(result),
            as_array(
                OGImage.apply_false_colour(
                    image_bytes=original,
                    original_image=False,
                    **expected_parameters,
                ),
            ),
        )

        # and they must make a difference, rather than being ignored
        unchanged = get_frame(
            test_app,
            login_and_get_token,
            1,
            colourmap_name="viridis",
        )
        assert not np.array_equal(as_array(result), as_array(unchanged))

    @pytest.mark.asyncio
    async def test_preferred_colourmap_is_used(
        self,
        reset_record_storage,
        test_app: TestClient,
        login_and_get_token,
    ):
        """With no `colourmap_name` the user's preferred colour map should be used."""
        await ingest_image_series(test_app, login_and_get_token)
        original = get_frame(test_app, login_and_get_token, 1, original_image=True)

        # This sets the preference to coolwarm
        set_preferred_colourmap(test_app, login_and_get_token, True)
        try:
            result = get_frame(test_app, login_and_get_token, 1)
        finally:
            unset_preferred_colourmap(test_app, login_and_get_token, True)

        np.testing.assert_array_equal(
            as_array(result),
            as_array(
                OGImage.apply_false_colour(
                    image_bytes=original,
                    original_image=False,
                    **{**DEFAULT_FALSE_COLOUR, "colourmap_name": "coolwarm"},
                ),
            ),
        )


class TestGetImageSeriesFrameCrosshair:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("frame_index", "position"),
        [
            pytest.param(0, [0, 1], id="frame 0"),
            pytest.param(1, [1, 0], id="frame 1"),
            pytest.param(2, [1, 1], id="frame 2"),
        ],
    )
    async def test_crosshair_at_position(
        self,
        reset_record_storage,
        test_app: TestClient,
        login_and_get_token,
        frame_index: int,
        position: list[int],
    ):
        """The row and column through the position, from the requested frame."""
        await ingest_image_series(test_app, login_and_get_token)
        frame = np.array(EXPECTED_FRAMES[frame_index])
        x, y = position

        response = test_app.get(
            frame_url(RECORD_ID_TMP, CHANNEL_NAME, frame_index) + "/crosshair",
            params={"position": json.dumps(position)},
            headers=auth(login_and_get_token),
        )

        assert response.status_code == 200
        body = response.json()
        assert body["row"]["position"] == y
        assert body["row"]["intensity"]["y"] == frame[y, :].tolist()
        assert body["column"]["position"] == x
        assert body["column"]["intensity"]["y"] == frame[:, x].tolist()
        assert isinstance(body["row"]["fwhm"], float)
        assert isinstance(body["column"]["fwhm"], float)

    @pytest.mark.asyncio
    async def test_crosshair_defaults_to_centroid(
        self,
        reset_record_storage,
        test_app: TestClient,
        login_and_get_token,
    ):
        await ingest_image_series(test_app, login_and_get_token)
        frame = np.array(EXPECTED_FRAMES[1])
        expected_x, expected_y = OGImage.validate_position(None, frame)

        response = test_app.get(
            frame_url(RECORD_ID_TMP, CHANNEL_NAME, 1) + "/crosshair",
            headers=auth(login_and_get_token),
        )

        assert response.status_code == 200
        body = response.json()
        assert body["column"]["position"] == expected_x
        assert body["row"]["position"] == expected_y

    @pytest.mark.asyncio
    async def test_crosshair_frame_index_out_of_range(
        self,
        reset_record_storage,
        test_app: TestClient,
        login_and_get_token,
    ):
        await ingest_image_series(test_app, login_and_get_token)

        response = test_app.get(
            frame_url(RECORD_ID_TMP, CHANNEL_NAME, len(EXPECTED_FRAMES)) + "/crosshair",
            headers=auth(login_and_get_token),
        )

        assert response.status_code == 400

    def test_crosshair_unauthorised(self, test_app: TestClient):
        response = test_app.get(
            frame_url(RECORD_ID_05_0800, CHANNEL_NAME, 0) + "/crosshair",
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_bits_are_shifted_back_to_raw_values(self):
        """
        A frame that was not 8 or 16 bit is stored shifted into the most significant
        bits, as for normal images. The crosshair should report the raw values, not
        the shifted ones.
        """
        raw = np.array([[0, 1024], [2048, 4095]], dtype=np.uint16)
        png = io.BytesIO()
        Image.fromarray(raw * 16).save(png, format="PNG")  # 12 bit, as stored

        with patch.object(
            ImageSeries,
            "get_frame",
            AsyncMock(return_value=png.getvalue()),
        ), patch.object(Record, "get_raw_bit_depth", AsyncMock(return_value=12)):
            array = await get_frame_array("record_id", CHANNEL_NAME, 0)

        np.testing.assert_array_equal(array, raw)
