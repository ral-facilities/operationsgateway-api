from pathlib import Path
from tempfile import SpooledTemporaryFile, TemporaryFile
from unittest.mock import patch

from fastapi.testclient import TestClient
import h5py
import numpy as np
import pytest
from pytest_mock import mocker, MockerFixture

from operationsgateway_api.src.config import BackupConfig
from operationsgateway_api.src.exceptions import DatabaseError, EchoS3Error
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
        record.attrs.create("timestamp", "2020-04-07T14:28:16+00:00")
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

        cm_202_cvc_wfs_coef = record.create_group("CM-202-CVC-WFS-COEF")
        cm_202_cvc_wfs_coef.attrs.create("channel_dtype", "vector")
        labels = [
            "Tilt X",
            "Tilt Y",
            "Defocus",
            "Astigmatism",
            "Oblique astigmatism",
            "Coma Y",
            "Coma X",
            "Trefoil",
            "Oblique trefoil",
            "Spherical",
            "Z_4^2",
            "Z_4^-2",
            "Z_4^4",
            "Z_4^-4",
            "Z_5^1",
            "Z_5^-1",
            "Z_5^3",
            "Z_5^-3",
            "Z_5^5",
            "Z_5^-5",
        ]
        cm_202_cvc_wfs_coef.attrs.create("labels", labels)
        data = [
            5.639372695195284,
            5.587336765253104,
            1.826101240997037,
            2.521215679028282,
            -2.980784658113992,
            -2.279530101757219,
            0.8275213451146765,
            -0.2507684324157028,
            -1.3952389582428177,
            -0.925578472683586,
            0.5665629489813115,
            0.6252987786682547,
            0.16671172514266414,
            0.0724989856677573,
            0.18313006266485013,
            0.26288446058591775,
            -0.03412582732888118,
            0.1467799869560521,
            0.16014661721357387,
            0.10650232684232015,
        ]
        cm_202_cvc_wfs_coef.create_dataset("data", data=np.array(data))


class TestSubmitHDF:
    @pytest.mark.asyncio
    async def test_ingest_data_success(
        self,
        reset_record_storage,
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
                    "CM-202-CVC-WFS",
                    "CM-202-CVC-WFS-COEF",
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
        reset_record_storage,
        test_app: TestClient,
        login_and_get_token,
        mocker: MockerFixture,
        tmp_path: Path,
    ):

        _ = await create_test_hdf_file()

        # Mock in the tmp_path fixture
        backup = BackupConfig(cache_directory=tmp_path)
        mocker.patch("operationsgateway_api.src.config.Config.config.backup", backup)

        test_file = "test.h5"
        files = {"file": (test_file, open(test_file, "rb"))}
        test_app.post(
            "/submit/hdf",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
            files=files,
        )
        cache_path_1 = tmp_path / "2020/04/07/142816/1.hdf5"
        assert cache_path_1.exists()
        assert cache_path_1.stat().st_size == 115056

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
                    "CM-202-CVC-WFS": channel_present_message,
                    "CM-202-CVC-WFS-COEF": channel_present_message,
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

        cache_path_2 = tmp_path / "2020/04/07/142816/2.hdf5"
        assert cache_path_2.exists()
        assert cache_path_2.stat().st_size == 115056

        temporary_file = SpooledTemporaryFile()
        with h5py.File(temporary_file, "w") as f:
            f.attrs.create("epac_ops_data_version", "1.0")
            record = f["/"]
            record.attrs.create("timestamp", "2020-04-07T14:28:16+00:00")
            record.attrs.create("shotnum", 366272, dtype="u8")
            record.attrs.create("active_area", "ea1")
            record.attrs.create("active_experiment", "90097341")
            group = record.create_group("PM-201-TJ-CRY-T")
            group.attrs.create("channel_dtype", "scalar")
            group.create_dataset("data", data=0)

        test_response = test_app.post(
            "/submit/hdf",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
            files={"file": (test_file, temporary_file)},
        )

        expected_response = {
            "message": "Updated 20200407142816",
            "response": {
                "accepted_channels": ["PM-201-TJ-CRY-T"],
                "rejected_channels": {},
                "warnings": [],
            },
        }
        assert test_response.json() == expected_response
        assert test_response.status_code == 200

        cache_path_3 = tmp_path / "2020/04/07/142816/3.hdf5"
        assert cache_path_3.exists()
        assert cache_path_3.stat().st_size == 7080


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
        reset_record_storage,
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
    async def test_channel_all_fail(
        self,
        reset_record_storage,
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
                "accepted_channels": ["CM-202-CVC-WFS-COEF"],
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
        reset_record_storage,
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
                    "CM-202-CVC-WFS-COEF": (
                        "Channel is already present in existing record"
                    ),
                    "PM-201-FE-CAM-2": [
                        "data has wrong datatype, should be ndarray",
                        "data has wrong datatype, should be uint16 or uint8",
                    ],
                    "PM-201-HJ-PD": "Channel is already present in existing record",
                },
                "warnings": [],
            },
        }

        assert test_response.json() == expected_response
        assert test_response.status_code == 200

    #  The DB is but ECHO is not accessible before ingestion starts.
    @pytest.mark.asyncio
    async def test_echo_failure_on_start(
        self,
        reset_record_storage,
        test_app: TestClient,
        login_and_get_token,
    ):
        with patch(
            "operationsgateway_api.src.records.echo_interface.EchoInterface.upload_file_object",
            side_effect=EchoS3Error(),
        ):
            create_integration_test_hdf()

            test_file = "test.h5"
            files = {"file": (test_file, open(test_file, "rb"))}

            test_response = test_app.post(
                "/submit/hdf",
                headers={"Authorization": f"Bearer {login_and_get_token}"},
                files=files,
            )

            assert test_response.status_code == 201

            expected_response = {
                "message": "Added as 20200407142816",
                "response": {
                    "accepted_channels": ["PM-201-TJ-CAM-2-FWHMY"],
                    "rejected_channels": {
                        "CM-202-CVC-WFS-COEF": ["Upload to Echo failed"],
                        "PM-201-FE-CAM-2": ["Upload to Echo failed"],
                        "PM-201-HJ-PD": ["Upload to Echo failed"],
                    },
                    "warnings": [],
                },
            }
            print("-----------------------")
            print(test_response.json())
            print("-----------------------")
            assert test_response.json() == expected_response

    # DB and ECHO become inaccessible mid-way through ingesting a NEW .h5 file
    @pytest.mark.asyncio
    async def test_partial_s3_and_db_upload_failure(
        self,
        reset_record_storage,
        test_app: TestClient,
        login_and_get_token,
    ):

        # Define a side_effect function for the mock upload
        def mock_upload_file_object(file_object, object_path):
            # Extract channel name from the path
            channel_name = object_path.split("/")[-1]
            if channel_name == "PM-201-FE-CAM-2.json":
                raise EchoS3Error()

        # Define a side_effect function for the database insert
        def mock_insert_one(collection_name, data):
            if "PM-201-HJ-PD" in data["channels"]:
                raise DatabaseError()

        # Patch both the S3 upload method and the MongoDB insert_one method
        with patch(
            "operationsgateway_api.src.records.echo_interface.EchoInterface.upload_file_object",
            side_effect=mock_upload_file_object,
        ), patch(
            "operationsgateway_api.src.mongo.interface.MongoDBInterface.insert_one",
            side_effect=mock_insert_one,
        ):

            # Create a test HDF file with the defined channels
            create_integration_test_hdf()

            # Simulate the file upload
            test_file = "test.h5"
            files = {"file": (test_file, open(test_file, "rb"))}

            # Call the endpoint
            test_response = test_app.post(
                "/submit/hdf",
                headers={"Authorization": f"Bearer {login_and_get_token}"},
                files=files,
            )

            # Check the status code
            assert test_response.status_code == 500

            assert test_response.json() == {"detail": "Database error"}

    # The DB is but ECHO is not accessible mid-way through ingesting a NEW .h5 file.
    @pytest.mark.asyncio
    async def test_partial_s3_upload_failure(
        self,
        reset_record_storage,
        test_app: TestClient,
        login_and_get_token,
    ):

        # Track uploaded channels
        uploaded_channels = []

        # Define a side_effect function for the mock
        def mock_upload_file_object(file_object, object_path):
            # Extract channel name from the path
            channel_name = object_path.split("/")[-1]
            if channel_name == "PM-201-HJ-PD.json":  # Simulate success for the first
                uploaded_channels.append(channel_name)
            else:
                raise EchoS3Error()

        # Patch the S3 upload method
        with patch(
            "operationsgateway_api.src.records.echo_interface.EchoInterface.upload_file_object",
            side_effect=mock_upload_file_object,
        ):
            # Create a test HDF file with the defined channels
            create_integration_test_hdf()

            # Simulate the file upload
            test_file = "test.h5"
            files = {"file": (test_file, open(test_file, "rb"))}

            # Call the endpoint
            test_response = test_app.post(
                "/submit/hdf",
                headers={"Authorization": f"Bearer {login_and_get_token}"},
                files=files,
            )

            # Check the status code
            assert test_response.status_code == 201

            expected_response = {
                "message": "Added as 20200407142816",
                "response": {
                    "accepted_channels": ["PM-201-HJ-PD", "PM-201-TJ-CAM-2-FWHMY"],
                    "rejected_channels": {
                        "CM-202-CVC-WFS-COEF": ["Upload to Echo failed"],
                        "PM-201-FE-CAM-2": ["Upload to Echo failed"],
                    },
                    "warnings": [],
                },
            }
            assert test_response.json() == expected_response

    # ECHO is but the db is not accessible mid-way through ingesting a NEW .h5 file.
    @pytest.mark.asyncio
    async def test_partial_db_failure(
        self,
        reset_record_storage,
        test_app: TestClient,
        login_and_get_token,
    ):

        # Define a side_effect function for the database insert
        def mock_insert_one(collection_name, data):
            if "PM-201-HJ-PD" in data["channels"]:
                raise DatabaseError()

        # Patch both the MongoDB insert_one method
        with patch(
            "operationsgateway_api.src.mongo.interface.MongoDBInterface.insert_one",
            side_effect=mock_insert_one,
        ):

            # Create a test HDF file with the defined channels
            create_integration_test_hdf()

            # Simulate the file upload
            test_file = "test.h5"
            files = {"file": (test_file, open(test_file, "rb"))}

            # Call the endpoint
            test_response = test_app.post(
                "/submit/hdf",
                headers={"Authorization": f"Bearer {login_and_get_token}"},
                files=files,
            )

            # Check the status code
            assert test_response.status_code == 500

            assert test_response.json() == {"detail": "Database error"}

    @pytest.mark.asyncio
    async def test_ingest_warning_on_incorrect_minor_version(
        self,
        reset_record_storage,
        test_app: TestClient,
        login_and_get_token,
    ):
        _ = await create_test_hdf_file()

        # Open and modify to an incorrect version number
        with h5py.File("test.h5", "a") as f:
            f.attrs.modify("epac_ops_data_version", "1.9")

        test_file = "test.h5"
        files = {"file": (test_file, open(test_file, "rb"))}

        test_response = test_app.post(
            "/submit/hdf",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
            files=files,
        )

        assert test_response.status_code == 201

        response_json = test_response.json()
        assert (
            "File minor version number too high (expected <=2)"
            in response_json["response"]["warnings"]
        )
