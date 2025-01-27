from fastapi.testclient import TestClient
import pytest


class TestGetUsers:
    @pytest.mark.asyncio
    async def test_get_users_success(
        self,
        test_app: TestClient,
        login_and_get_token,
    ):
        # Expected users to validate
        expected_users = [
            {
                "username": "frontend",
                "auth_type": "local",
                "authorised_routes": [],
            },
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
        ]

        response = test_app.get(
            "/users",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )
        assert response.status_code == 200

        response_data = response.json()

        # Filter the response to only include `frontend` and `backend` users
        users_to_validate = [
            user
            for user in response_data["users"]
            if user["username"] in {"frontend", "backend"}
        ]

        # Validate the filtered users, we have to be careful
        # because the response from the DB can be in any order
        for user_in_response in users_to_validate:
            matching_user = next(
                (
                    expected_user
                    for expected_user in expected_users
                    if expected_user["username"] == user_in_response["username"]
                ),
                None,
            )

            assert user_in_response["auth_type"] == matching_user["auth_type"]

            # Convert lists to sets for order-independent comparison
            assert set(user_in_response["authorised_routes"]) == set(
                matching_user["authorised_routes"],
            )

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
