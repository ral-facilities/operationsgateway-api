from fastapi.testclient import TestClient
import pytest

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
            "/users PATCH",
            "/users/{id_} DELETE",
            "/users GET",
        ],
    },
    {
        "username": "hdf_import",
        "auth_type": "local",
        "authorised_routes": ["/submit/hdf POST", "/submit/manifest POST"],
    },
    {"username": "local_user_no_password", "auth_type": "local", "authorised_routes": []},
]


class TestGetUsers:
    @pytest.mark.asyncio
    async def test_get_users_success(
        self,
        test_app: TestClient,
        login_and_get_token,
    ):
        response = test_app.get(
            "/users",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )
        assert response.status_code == 200
        response_data = response.json()
        # Validate each user in the response
        assert len(response_data["users"]) == len(expected_users)
        for user in response_data["users"]:
            # Check if the user exists in the expected users
            matching_user = next((u for u in expected_users if u["username"] == user["username"]), None)
            assert matching_user is not None, f"Unexpected user: {user['username']}"
            assert user["auth_type"] == matching_user["auth_type"]
            assert user["authorised_routes"] == matching_user["authorised_routes"]