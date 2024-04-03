from fastapi.testclient import TestClient
import pytest

from operationsgateway_api.src.records.record import Record


class TestDeleteRecordById:
    @pytest.mark.asyncio
    async def test_delete_record_success(
        self,
        test_app: TestClient,
        login_and_get_token,
    ):
        record_id = 19000000000011
        test_record = {
            "_id": "19000000000011",
            "metadata": {
                "epac_ops_data_version": "1.0",
                "shotnum": 423648000000,
                "timestamp": "2023-06-05T08:00:00",
            },
            "channels": {
                "test-scalar-channel-id": {
                    "metadata": {"channel_dtype": "scalar", "units": "µm"},
                    "data": 5.126920467610521,
                },
            },
        }

        record_instance = Record(test_record)
        await record_instance.insert()

        delete_response = test_app.delete(
            f"/records/{record_id}",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert delete_response.status_code == 204
        assert (await record_instance.find_existing_record()) is None
