import pytest
from fastapi.testclient import TestClient
from test.records.ingestion.create_test_hdf import create_test_hdf_file
from test.endpoints.conftest import reset_record_storage

class TestIngestionValidationRules:
    @pytest.mark.parametrize(
        "timestamp, shotnum, expected_status, expected_detail",
        [
            # Test 1: New Timestamp, No Shot Number
            ("2020-04-07T14:28:16+00:00", None, 201, None),
        ],
    )
    @pytest.mark.asyncio
    async def test_ingestion_rule_scenario(
        self,
        test_app: TestClient,
        reset_record_storage,
        login_and_get_token,
        timestamp,
        shotnum,
        expected_status,
        expected_detail,
    ):
        await create_test_hdf_file(timestamp=[timestamp, "exists"])


        test_file = "test.h5"
        files = {"file": (test_file, open(test_file, "rb"))}

        response = test_app.post(
            "/submit/hdf",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
            files=files,
        )

        assert response.status_code == expected_status
        if expected_status == 400:
            assert response.json()["detail"].lower() == expected_detail.lower()
