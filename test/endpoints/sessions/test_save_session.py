from datetime import datetime
from unittest.mock import patch

from bson import ObjectId
from fastapi.testclient import TestClient

from test.endpoints.sessions.conftest import Session


class TestSaveSession:
    @patch("operationsgateway_api.src.routes.sessions.datetime")
    def test_save_session(
        self,
        mock_datetime,
        test_app: TestClient,
        login_and_get_token,
    ):
        mock_datetime.now.return_value = datetime.fromisoformat("2023-06-01T13:00:00")
        mock_datetime.strftime.return_value = datetime.strftime(
            mock_datetime.now.return_value,
            "%Y-%m-%d %H:%M:%S",
        )

        name = "Test Saving Session"
        summary = "Test Summary"
        auto_saved = False
        session_data = {"data": 1234, "test": "5678"}

        test_response = test_app.post(
            f"/sessions?name={name}&summary={summary}&auto_saved={auto_saved}",
            json=session_data,
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_response.status_code == 201

        # Check the response is a valid object ID
        session_id = test_response.json()
        ObjectId(session_id)

        test_session = Session()
        query_result = test_session.find_one(session_id)
        assert query_result is not None

        test_session.delete(session_id)
