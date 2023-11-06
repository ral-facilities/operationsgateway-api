from fastapi.testclient import TestClient
import pytest


class TestDeleteUsers:
    def test_delete_local_user_success(
        self,
        test_app: TestClient,
        login_and_get_token,
        add_delete_local_fixture,
    ):
        delete_local_response = test_app.delete(
            "/users/testuserthatdoesnotexistinthedatabaselocal",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert delete_local_response.status_code == 204

    def test_delete_fed_user_success(
        self,
        test_app: TestClient,
        login_and_get_token,
        add_delete_fed_fixture,
    ):
        delete_fed_response = test_app.delete(
            "/users/testuserthatdoesnotexistinthedatabasefed",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert delete_fed_response.status_code == 204

    @pytest.mark.parametrize(
        "username",
        ["testuserthatdoesnotexistinthedatabase"],
        ids=["test_delete_user_fail"],
    )
    def test_delete_user_fail(
        self,
        username: str,
        test_app: TestClient,
        login_and_get_token,
    ):
        delete_response = test_app.delete(
            "/users/testuserthatdoesnotexistinthedatabase",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert delete_response.status_code == 500

    def test_delete_fed_user_forbidden(
        self,
        test_app: TestClient,
        add_delete_fed_fixture,
    ):
        delete_fed_response = test_app.delete(
            "/users/testuserthatdoesnotexistinthedatabasefed",
        )

        assert delete_fed_response.status_code == 403

    def test_delete_local_user_forbidden(
        self,
        test_app: TestClient,
        add_delete_local_fixture,
    ):
        delete_fed_response = test_app.delete(
            "/users/testuserthatdoesnotexistinthedatabaselocal",
        )

        assert delete_fed_response.status_code == 403
