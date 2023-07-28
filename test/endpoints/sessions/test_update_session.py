from datetime import datetime
from unittest.mock import patch

from fastapi.testclient import TestClient
import pytest

from test.endpoints.sessions.conftest import Session


class TestUpdateSession:
    # Builtins written in C cannot be directed patched, you have to patch the module
    # that it's being used in. See 'Partial mocking' in the unittest.mocking
    # documentation
    @patch("operationsgateway_api.src.routes.sessions.datetime")
    def test_update_session(
        self,
        mock_datetime,
        single_user_session,
        test_app: TestClient,
        login_and_get_token,
    ):
        mock_datetime.now.return_value = datetime.fromisoformat("2023-06-01T13:00:00")
        mock_datetime.strftime.return_value = datetime.strftime(
            mock_datetime.now.return_value,
            "%Y-%m-%d %H:%M:%S",
        )

        updated_name = "My Updated Test Session"
        updated_summary = "My Updated Summary"
        updated_auto_saved = False
        updated_body = {"myData": 123456789}

        test_response = test_app.patch(
            f"/sessions/{single_user_session['_id']}?name={updated_name}&summary="
            f"{updated_summary}&auto_saved={updated_auto_saved}",
            json=updated_body,
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_response.status_code == 200
        assert test_response.json() == f"Updated {single_user_session['_id']}"

        test_session = Session()
        updated_session = test_session.find_one(single_user_session["_id"])

        expected_session = single_user_session
        expected_session["name"] = updated_name
        expected_session["summary"] = updated_summary
        expected_session["auto_saved"] = updated_auto_saved
        expected_session["session"] = updated_body

        assert updated_session == expected_session

    @pytest.mark.parametrize(
        "session_id, auto_saved, expected_status_code",
        [
            pytest.param(
                "64789841c7a7319be3036150",
                "abc",
                422,
                id="Pydantic validation error",
            ),
            pytest.param("abc123", True, 400, id="Invalid ID"),
        ],
    )
    def test_invalid_update_session(
        self,
        test_app: TestClient,
        login_and_get_token,
        session_id,
        auto_saved,
        expected_status_code,
    ):
        name = "Test Name"
        summary = "Test Summary"
        body = {"data": 123}

        test_response = test_app.patch(
            f"/sessions/{session_id}?name={name}&summary={summary}"
            f"&auto_saved={auto_saved}",
            json=body,
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_response.status_code == expected_status_code
