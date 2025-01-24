from fastapi.testclient import TestClient
import pytest


class TestGetUsers:
    @pytest.mark.asyncio
    async def test_get_users_success(
        self,
        test_app: TestClient,
        login_and_get_token,
    ):
        expected_backend_user = {
            "username": "backend",
            "auth_type": "local",
            "authorised_routes": [
                "/submit/hdf POST",
                "/submit/manifest POST",
                "/records/{id_} DELETE",
                "/experiments POST",
                "/users POST",
                "/users PATCH",
                "/users/{id_} DELETE",
                "/users GET",
            ],
        }

        response = test_app.get(
            "/users",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )
        assert response.status_code == 200
        response_data = response.json()
        assert expected_backend_user in response_data["users"]

    @pytest.mark.asyncio
    async def test_get_users_unauthorised(
        self,
        test_app: TestClient,
        login_as_frontend_and_get_token,
    ):
        response = test_app.get(
            "/users",
            headers={"Authorization": f"Bearer {login_as_frontend_and_get_token}"},
        )
        assert response.status_code == 403

        expected_message = (
            "User 'frontend' is not authorised to use endpoint '/users GET'"
        )
        assert expected_message in response.text
