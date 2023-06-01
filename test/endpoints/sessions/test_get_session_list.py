from fastapi.testclient import TestClient


class TestGetSessionList:
    def test_get_session_list(
        self,
        multiple_user_sessions,
        test_app: TestClient,
        login_and_get_token,
    ):
        test_response = test_app.get(
            "/sessions/list",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        for session in multiple_user_sessions:
            del session["username"]
            del session["session"]

        assert test_response.status_code == 200
        assert test_response.json() == multiple_user_sessions
