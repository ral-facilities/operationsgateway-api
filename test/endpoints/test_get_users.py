from fastapi.testclient import TestClient
import pytest


class TestGetUsers:
    @pytest.mark.asyncio
    async def test_get_users_success(
        self,
        test_app: TestClient,
        login_and_get_token,
    ):
        # Expected user data for validation
        expected_users = [
            {"username": "rqw38472", "auth_type": "FedID", "authorised_routes": []},
            {"username": "xfu59478", "auth_type": "FedID", "authorised_routes": []},
            {"username": "dgs12138", "auth_type": "FedID", "authorised_routes": []},
            {"username": "frontend", "auth_type": "local", "authorised_routes": []},
            {
                "username": "backend",
                "auth_type": "local",
                "authorised_routes": [
                    "/submit/hdf POST",
                    "/submit/manifest POST",
                    "/records/{id_} DELETE",
                    "/experiments POST",
                    "/users POST",
                    "/users GET",
                    "/users PATCH",
                    "/users/{id_} DELETE",
                ],
            },
            {
                "username": "hdf_import",
                "auth_type": "local",
                "authorised_routes": ["/submit/hdf POST", "/submit/manifest POST"],
            },
            {
                "username": "local_user_no_password",
                "auth_type": "local",
                "authorised_routes": [],
            },
        ]

        response = test_app.get(
            "/users",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )
        assert response.status_code == 200
        response_data = response.json()
        assert response_data == expected_users

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
