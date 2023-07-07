from fastapi.testclient import TestClient

from test.endpoints.sessions.conftest import Session


class TestDeleteSession:
    def test_delete_session(
        self,
        single_user_session,
        test_app: TestClient,
        login_and_get_token,
    ):
        test_response = test_app.delete(
            f"/sessions/{single_user_session['_id']}",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_response.status_code == 204

        test_session = Session()
        deleted_session = test_session.find_one(single_user_session["_id"])

        assert deleted_session is None
