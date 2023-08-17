from fastapi.testclient import TestClient


class TestGetSession:
    def test_get_session(
        self,
        single_user_session,
        test_app: TestClient,
        login_and_get_token,
    ):
        test_response = test_app.get(
            f"/sessions/{single_user_session['_id']}",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_response.status_code == 200
        assert test_response.json() == single_user_session
