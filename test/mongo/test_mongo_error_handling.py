from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
import pytest


class TestMongoDBErrorHandling:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "record_id, expected_status_code, expected_response",
        [
            pytest.param(
                "20230605100000",
                500,
                {"detail": "Database operation failed during find_one"},
                id="Simulated error during find_one",
            ),
        ],
    )
    # This test simulates an exception being raised in the collection.find_one call
    # (within interface.py), which the decorator should handle and produce a
    # DatabaseError, ultimately flowing this back up to the user in the endpoint,
    # producing a 500
    async def test_find_one_exception_in_interface(
        self,
        test_app: TestClient,
        login_and_get_token,
        record_id,
        expected_status_code,
        expected_response,
    ):
        with patch(
            "operationsgateway_api.src.mongo.interface.MongoDBInterface.get_collection_object",
        ) as mock_get_collection_object:
            # Mock the `collection.find_one` to raise an exception
            mock_collection = AsyncMock()
            mock_collection.find_one.side_effect = Exception("Simulated exception")
            mock_get_collection_object.return_value = mock_collection

            # Make the GET request to the endpoint
            response = test_app.get(
                f"/records/{record_id}",
                headers={"Authorization": f"Bearer {login_and_get_token}"},
            )

            # Assert the status code and responseAsyncMock
            assert response.status_code == expected_status_code
            assert response.json() == expected_response
