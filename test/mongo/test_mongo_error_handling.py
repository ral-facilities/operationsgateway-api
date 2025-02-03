from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
import pytest

from operationsgateway_api.src.exceptions import DatabaseError
from operationsgateway_api.src.mongo.mongo_error_handling import mongodb_error_handling


class TestMongoDBErrorHandling:

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
    @pytest.mark.asyncio
    async def test_async_integration_failure(
        self,
        test_app: TestClient,
        login_and_get_token,
        record_id,
        expected_status_code,
        expected_response,
    ):
        """This test simulates an exception being raised in the collection.find_one call
        (within interface.py), which the decorator should handle and produce a
        DatabaseError, ultimately flowing this back up to the user in the endpoint,
        producing a 500"""

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

    @pytest.mark.asyncio
    async def test_async_unit_success(self):
        """Ensure the async decorator allows normal execution
        if no exception occurs."""

        @mongodb_error_handling("find_one")
        async def mock_find_one():
            return {"key": "value"}

        result = await mock_find_one()
        assert result == {"key": "value"}

    def test_sync_unit_failure(self):
        """Test the sync version of the MongoDB error
        handling decorator in isolation."""

        @mongodb_error_handling("insert_one")
        def mock_insert_one():
            raise Exception("Simulated database error")

        with patch(
            "operationsgateway_api.src.mongo.mongo_error_handling.log",
        ) as mock_log:
            with pytest.raises(DatabaseError) as exc_info:
                mock_insert_one()

            assert "Database operation failed during insert_one" in str(exc_info.value)
            mock_log.error.assert_called_once_with(
                "Database operation: %s failed",
                "insert_one",
            )

    def test_sync_unit_success(self):
        """Ensure the sync decorator allows normal execution if no exception occurs."""

        @mongodb_error_handling("insert_one")
        def mock_insert_one():
            return {"key": "value"}

        result = mock_insert_one()
        assert result == {"key": "value"}
