from fastapi.testclient import TestClient
import h5py
import numpy as np
import pytest

from test.records.ingestion.create_test_hdf import create_test_hdf_file


def create_integration_test_hdf(fails=None, generic_fail=None):
    """
    Creates a smaller HDF file similar to the other function but much smaller this
    function also doesn't run hdf_handler.py to allow better use of the integration
    tests
    """
    if not fails:
        fails = []
    if not generic_fail:
        generic_fail = []

    with h5py.File("test.h5", "w") as f:
        f.attrs.create("epac_ops_data_version", "1.0")
        record = f["/"]
        record.attrs.create("timestamp", "2020-04-07 14:28:16")
        record.attrs.create("shotnum", 366272, dtype="u8")
        record.attrs.create("active_area", "ea1")
        record.attrs.create("active_experiment", "90097341")

        if "scalar" in fails:
            pm_201_tj_cam_2_fwhmy = record.create_group("FALSE_SCALAR")
        else:
            pm_201_tj_cam_2_fwhmy = record.create_group("PM-201-TJ-CAM-2-FWHMY")
        pm_201_tj_cam_2_fwhmy.attrs.create("channel_dtype", "scalar")
        if "scalar" in generic_fail:
            pm_201_tj_cam_2_fwhmy.create_dataset("data", data=["GS"])
        else:
            pm_201_tj_cam_2_fwhmy.create_dataset("data", data="GS")

        if "image" in fails:
            pm_201_fe_cam_2 = record.create_group("FALSE_IMAGE")
        else:
            pm_201_fe_cam_2 = record.create_group("PM-201-FE-CAM-2")

        pm_201_fe_cam_2.attrs.create("channel_dtype", "image")
        pm_201_fe_cam_2.attrs.create("exposure_time_s", 0.001)
        pm_201_fe_cam_2.attrs.create("gain", 5.5)
        pm_201_fe_cam_2.attrs.create("x_pixel_size", 441.0)
        pm_201_fe_cam_2.attrs.create("x_pixel_units", "µm")
        pm_201_fe_cam_2.attrs.create("y_pixel_size", 441.0)
        pm_201_fe_cam_2.attrs.create("y_pixel_units", "µm")
        data = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]], dtype=np.uint16)

        if "image" in generic_fail:
            pm_201_fe_cam_2.create_dataset("data", data=12)
        else:
            pm_201_fe_cam_2.create_dataset("data", data=data)

        if "waveform" in fails:
            pm_201_hj_pd = record.create_group("FALSE_WAVEFORM")
        else:
            pm_201_hj_pd = record.create_group("PM-201-HJ-PD")

        pm_201_hj_pd.attrs.create("channel_dtype", "waveform")
        pm_201_hj_pd.attrs.create("x_units", "s")
        pm_201_hj_pd.attrs.create("y_units", "kJ")
        x = [1, 2, 3, 4, 5, 5456]
        y = [8, 3, 6, 2, 3, 8]
        pm_201_hj_pd.create_dataset("x", data=x)

        if "waveform" in generic_fail:
            pm_201_hj_pd.create_dataset("y", data=2)
        else:
            pm_201_hj_pd.create_dataset("y", data=y)


class TestIntegrationIngestData:
    @pytest.mark.asyncio
    async def test_ingest_data_success(
        self,
        reset_databases,
        test_app: TestClient,
        login_and_get_token,
    ):

        _ = await create_test_hdf_file()

        test_file = "test.h5"
        files = {"file": (test_file, open(test_file, "rb"))}
        test_response = test_app.post(
            "/submit/hdf",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
            files=files,
        )

        expected_response = {
            "message": "Added as 20200407142816",
            "response": {
                "accepted_channels": [
                    "PM-201-FE-CAM-1",
                    "PM-201-FE-CAM-2",
                    "PM-201-FE-CAM-2-CENX",
                    "PM-201-FE-CAM-2-CENY",
                    "PM-201-FE-CAM-2-FWHMX",
                    "PM-201-FE-CAM-2-FWHMY",
                    "PM-201-FE-EM",
                    "PM-201-HJ-PD",
                    "PM-201-PA1-EM",
                    "PM-201-PA2-EM",
                    "PM-201-TJ-CAM-2-CENX",
                    "PM-201-TJ-CAM-2-CENY",
                    "PM-201-TJ-CAM-2-FWHMX",
                    "PM-201-TJ-CAM-2-FWHMY",
                    "PM-201-TJ-EM",
                ],
                "rejected_channels": {},
                "warnings": [],
            },
        }
        assert test_response.json() == expected_response
        assert test_response.status_code == 201

    @pytest.mark.asyncio
    async def test_merge_record_success(
        self,
        reset_databases,
        test_app: TestClient,
        login_and_get_token,
    ):

        _ = await create_test_hdf_file()

        test_file = "test.h5"
        files = {"file": (test_file, open(test_file, "rb"))}
        test_app.post(
            "/submit/hdf",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
            files=files,
        )

        test_response = test_app.post(
            "/submit/hdf",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
            files=files,
        )

        channel_present_message = "Channel is already present in existing record"
        expected_response = {
            "message": "Updated 20200407142816",
            "response": {
                "accepted_channels": [],
                "rejected_channels": {
                    "PM-201-FE-CAM-1": channel_present_message,
                    "PM-201-FE-CAM-2": channel_present_message,
                    "PM-201-FE-CAM-2-CENX": channel_present_message,
                    "PM-201-FE-CAM-2-CENY": channel_present_message,
                    "PM-201-FE-CAM-2-FWHMX": channel_present_message,
                    "PM-201-FE-CAM-2-FWHMY": channel_present_message,
                    "PM-201-FE-EM": channel_present_message,
                    "PM-201-HJ-PD": channel_present_message,
                    "PM-201-PA1-EM": channel_present_message,
                    "PM-201-PA2-EM": channel_present_message,
                    "PM-201-TJ-CAM-2-CENX": channel_present_message,
                    "PM-201-TJ-CAM-2-CENY": channel_present_message,
                    "PM-201-TJ-CAM-2-FWHMX": channel_present_message,
                    "PM-201-TJ-CAM-2-FWHMY": channel_present_message,
                    "PM-201-TJ-EM": channel_present_message,
                },
                "warnings": [],
            },
        }

        assert test_response.json() == expected_response
        assert test_response.status_code == 200

    @pytest.mark.parametrize(
        "data_version, active_area, expected_response",
        [
            pytest.param(
                ["1.0", "missing"],
                None,
                {"detail": "epac_ops_data_version does not exist"},
                id="Reject file",
            ),
            pytest.param(
                None,
                ["ea1", "missing"],
                {"detail": "active_area is missing"},
                id="Reject record",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_hdf_rejects(
        self,
        data_version,
        active_area,
        expected_response,
        reset_databases,
        test_app: TestClient,
        login_and_get_token,
    ):
        _ = await create_test_hdf_file(
            data_version=data_version,
            active_area=active_area,
        )

        test_file = "test.h5"
        files = {"file": (test_file, open(test_file, "rb"))}

        test_response = test_app.post(
            "/submit/hdf",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
            files=files,
        )

        assert test_response.json() == expected_response
        assert test_response.status_code == 400

    @pytest.mark.asyncio
    async def test_partial_import_record_reject(
        self,
        reset_databases,
        test_app: TestClient,
        login_and_get_token,
    ):
        _ = await create_test_hdf_file()

        test_file = "test.h5"
        files = {"file": (test_file, open(test_file, "rb"))}

        test_app.post(
            "/submit/hdf",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
            files=files,
        )

        _ = await create_test_hdf_file(shotnum=["valid", "missing"])

        files = {"file": (test_file, open(test_file, "rb"))}

        test_response = test_app.post(
            "/submit/hdf",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
            files=files,
        )

        assert test_response.json() == {"detail": "inconsistent metadata"}
        assert test_response.status_code == 400

    @pytest.mark.asyncio
    async def test_partial_import_timestamp_match(
        self,
        reset_databases,
        test_app: TestClient,
        login_and_get_token,
    ):
        _ = await create_test_hdf_file()

        test_file = "test.h5"
        files = {"file": (test_file, open(test_file, "rb"))}

        test_app.post(
            "/submit/hdf",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
            files=files,
        )

        _ = await create_test_hdf_file(
            shotnum=["valid", "missing"],
            data_version=["1.0", "missing"],
            active_area=["ea1", "missing"],
            active_experiment=["90097341", "missing"],
        )

        files = {"file": (test_file, open(test_file, "rb"))}

        test_response = test_app.post(
            "/submit/hdf",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
            files=files,
        )

        assert test_response.json() == {
            "detail": "timestamp matches, other metadata does not",
        }
        assert test_response.status_code == 400

    @pytest.mark.asyncio
    async def test_channel_all_fail(
        self,
        reset_databases,
        test_app: TestClient,
        login_and_get_token,
    ):
        create_integration_test_hdf(fails=["scalar", "image", "waveform"])

        test_file = "test.h5"
        files = {"file": (test_file, open(test_file, "rb"))}

        test_response = test_app.post(
            "/submit/hdf",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
            files=files,
        )

        expected_response = {
            "message": "Added as 20200407142816",
            "response": {
                "accepted_channels": [],
                "rejected_channels": {
                    "FALSE_IMAGE": [
                        "Channel name is not recognised (does not appear in manifest)",
                    ],
                    "FALSE_SCALAR": [
                        "Channel name is not recognised (does not appear in manifest)",
                    ],
                    "FALSE_WAVEFORM": [
                        "Channel name is not recognised (does not appear in manifest)",
                    ],
                },
                "warnings": [],
            },
        }

        assert test_response.json() == expected_response
        assert test_response.status_code == 201

    @pytest.mark.asyncio
    async def test_channel_multiple_reject_types(
        self,
        reset_databases,
        test_app: TestClient,
        login_and_get_token,
    ):
        create_integration_test_hdf(fails=["scalar"])

        test_file = "test.h5"
        files = {"file": (test_file, open(test_file, "rb"))}

        test_app.post(
            "/submit/hdf",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
            files=files,
        )

        create_integration_test_hdf(generic_fail=["image"])

        files = {"file": (test_file, open(test_file, "rb"))}

        test_response = test_app.post(
            "/submit/hdf",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
            files=files,
        )

        expected_response = {
            "message": "Updated 20200407142816",
            "response": {
                "accepted_channels": ["PM-201-TJ-CAM-2-FWHMY"],
                "rejected_channels": {
                    "PM-201-FE-CAM-2": [
                        "data attribute has wrong datatype, should be ndarray",
                        "data attribute has wrong datatype, should be uint16 or uint8",
                    ],
                    "PM-201-HJ-PD": "Channel is already present in existing record",
                },
                "warnings": [],
            },
        }

        assert test_response.json() == expected_response
        assert test_response.status_code == 200
