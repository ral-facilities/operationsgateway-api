import io

from fastapi.testclient import TestClient
import numpy as np
from PIL import Image
import pytest

from test.conftest import (
    IMAGE_SERIES_FRAMES,
    RECORD_ID_05_0800,
    RECORD_ID_TMP,
)
from test.records.ingestion.create_test_hdf import create_test_hdf_file

CHANNEL_NAME = "TEST_IMAGE_SERIES"
EXPECTED_FRAMES = IMAGE_SERIES_FRAMES


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
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "image/png"

        with Image.open(io.BytesIO(response.content)) as image:
            np.testing.assert_array_equal(
                np.array(image),
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

        contents = set()
        for frame_index in range(len(EXPECTED_FRAMES)):
            response = test_app.get(
                frame_url(RECORD_ID_TMP, CHANNEL_NAME, frame_index),
                headers={"Authorization": f"Bearer {login_and_get_token}"},
            )
            assert response.status_code == 200
            contents.add(response.content)

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
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert response.status_code == 400

    def test_negative_frame_index_rejected(
        self,
        test_app: TestClient,
        login_and_get_token,
    ):
        """`frame_index` is declared as ge=0, so this fails validation."""
        response = test_app.get(
            frame_url(RECORD_ID_05_0800, CHANNEL_NAME, -1),
            headers={"Authorization": f"Bearer {login_and_get_token}"},
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
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert response.status_code == 400

    def test_unknown_channel(self, test_app: TestClient, login_and_get_token):
        response = test_app.get(
            frame_url(RECORD_ID_05_0800, "NOT_A_CHANNEL", 0),
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert response.status_code == 404

    def test_unauthorised(self, test_app: TestClient):
        response = test_app.get(frame_url(RECORD_ID_05_0800, CHANNEL_NAME, 0))

        assert response.status_code == 401
