import io
import json
from zipfile import ZipFile

from fastapi.testclient import TestClient
import h5py
import numpy as np
from PIL import Image

from test.conftest import IMAGE_SERIES_CHANNEL_NAME, MARK_EPAC_TEST, RECORD_ID_TMP

FRAMES = np.array(
    [
        [[0, 255], [256, 4095]],
        [[65535, 1], [32768, 1024]],
        [[42, 128], [2048, 8192]],
    ],
    dtype=np.uint16,
)


def create_image_series_hdf_file() -> None:
    with h5py.File("test.h5", "w") as f:
        f.attrs.create("epac_ops_data_version", "1.0")
        record = f["/"]
        record.attrs.create("timestamp", "2020-04-07T14:28:16+00:00")
        record.attrs.create("shotnum", 366272, dtype="u8")
        record.attrs.create("active_area", "ea1")
        record.attrs.create("active_experiment", "90097341")

        image_series = record.create_group(IMAGE_SERIES_CHANNEL_NAME)
        image_series.attrs.create("channel_dtype", "image_series")
        image_series.attrs.create("frame_rate_hz", 100.0)
        image_series.create_dataset("data", data=FRAMES)


@MARK_EPAC_TEST
class TestGetImageSeriesFrame:
    def test_submit_series_success(
        self,
        reset_record_storage,
        test_app: TestClient,
        login_and_get_token,
    ):
        """
        Submit an HDF file containing an image series of 3 frames, then
        get the middle frame back through the API and check it is the right one.
        """
        headers = {"Authorization": f"Bearer {login_and_get_token}"}
        create_image_series_hdf_file()

        with open("test.h5", "rb") as file:
            submit_response = test_app.post(
                "/submit/hdf",
                headers=headers,
                files={"file": ("test.h5", file)},
            )
        assert submit_response.status_code == 201, submit_response.text

        response = test_app.get(
            f"/image-series/{RECORD_ID_TMP}/{IMAGE_SERIES_CHANNEL_NAME}/frames/1",
            params={"original_image": True},
            headers=headers,
        )

        assert response.status_code == 200, response.text
        assert response.headers["content-type"] == "image/png"
        with Image.open(io.BytesIO(response.content)) as image:
            np.testing.assert_array_equal(np.array(image), FRAMES[1])


@MARK_EPAC_TEST
class TestGetImageSeriesCrosshair:
    def test_get_middle_frame_crosshair(
        self,
        reset_record_storage,
        test_app: TestClient,
        login_and_get_token,
    ):
        """
        Submit an HDF file containing an image series of 3 frames, then
        get the crosshair for the middle frame at a given position and check the row
        and column are the pixels of that frame through that position.
        """
        headers = {"Authorization": f"Bearer {login_and_get_token}"}
        create_image_series_hdf_file()

        with open("test.h5", "rb") as file:
            submit_response = test_app.post(
                "/submit/hdf",
                headers=headers,
                files={"file": ("test.h5", file)},
            )
        assert submit_response.status_code == 201, submit_response.text

        response = test_app.get(
            f"/image-series/{RECORD_ID_TMP}/{IMAGE_SERIES_CHANNEL_NAME}/frames/1/crosshair",
            params={"position": json.dumps([1, 0])},  # x is 1, y is 0
            headers=headers,
        )

        assert response.status_code == 200, response.text
        crosshair = response.json()

        row_pixels = crosshair["row"]["intensity"]["y"]
        column_pixels = crosshair["column"]["intensity"]["y"]

        assert crosshair["row"]["position"] == 0
        assert row_pixels == [65535, 1]
        assert crosshair["column"]["position"] == 1
        assert column_pixels == [1, 1024]


@MARK_EPAC_TEST
class TestExportImageSeries:
    def test_export_contents_success(
        self,
        reset_record_storage,
        test_app: TestClient,
        login_and_get_token,
    ):
        """
        Submit an HDF file containing an image series of 3 frames, then
        export the record and check the zip holds the whole series as a .npy file,
        alongside the csv, with the same frames that were submitted.
        """
        headers = {"Authorization": f"Bearer {login_and_get_token}"}
        create_image_series_hdf_file()

        with open("test.h5", "rb") as file:
            submit_response = test_app.post(
                "/submit/hdf",
                headers=headers,
                files={"file": ("test.h5", file)},
            )
        assert submit_response.status_code == 201, submit_response.text

        export_response = test_app.get(
            "/export",
            params={
                "conditions": json.dumps({"_id": {"$eq": RECORD_ID_TMP}}),
                "projection": [
                    "metadata.timestamp",
                    f"channels.{IMAGE_SERIES_CHANNEL_NAME}",
                ],
                "export_images": True,
            },
            headers=headers,
        )

        assert export_response.status_code == 200, export_response.text
        assert export_response.headers["content-type"] == "application/zip"
        npy_filename = f"{RECORD_ID_TMP}_{IMAGE_SERIES_CHANNEL_NAME}.npy"

        with ZipFile(io.BytesIO(export_response.content)) as zip_file:
            assert sorted(zip_file.namelist()) == [f"{RECORD_ID_TMP}.csv", npy_filename]
            exported = np.load(zip_file.open(npy_filename))
        np.testing.assert_array_equal(exported, FRAMES)
