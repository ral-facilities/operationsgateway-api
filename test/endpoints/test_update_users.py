import json

from fastapi.testclient import TestClient
import pytest

""" {
    "_id": "testuserthatdoesnotexistinthedatabaselocal",
    "auth_type": "local",
    "authorised_routes": ["/submit/hdf POST", "/experiments POST"],
    "sha256_password": "password",
}

{
    "_id": "testuserthatdoesnotexistinthedatabasefed",
    "auth_type": "FedID",
    "authorised_routes": ["/submit/hdf POST", "/experiments POST"],
}

{
    "_id": "username",
    "updated_password": "password",
    "add_authorised_routes": ["/submit/hdf POST", "/experiments POST"],
    "remove_authorised_routes": ["/submit/hdf POST"]
} """


class TestUpdateUsers:
    @pytest.mark.parametrize(
        "username, updated_password, add_authorised_routes, "
        "remove_authorised_routes, expected_response_code",
        [
            pytest.param(
                "testuserthatdoesnotexistinthedatabaselocal",
                "passwords",
                [],
                [],
                200,
                id="Successful local user password update",
            ),
            pytest.param(
                "testuserthatdoesnotexistinthedatabaselocal",
                "password",
                [],
                [],
                200,
                id="Updating the password to itself",
            ),
            pytest.param(
                "testuserthatdoesnotexistinthedatabaselocal",
                None,
                [],
                [],
                200,
                id="Successfully updating nothing",
            ),
            pytest.param(
                "testuserthatdoesnotexistinthedatabaselocal",  #
                None,
                None,
                [],
                200,
                id="Successfully updating nothing (empty add routes)",
            ),
            pytest.param(
                "testuserthatdoesnotexistinthedatabaselocal",  #
                None,
                [],
                None,
                200,
                id="Successfully updating nothing (empty add routes)",
            ),
            pytest.param(
                "testuserthatdoesnotexistinthedatabaselocal",  #
                None,
                None,
                None,
                200,
                id="Successfully updating nothing (empty routes)",
            ),
            pytest.param(
                "testuserthatdoesnotexistinthedatabaselocal",
                None,
                ["/records/{id_} DELETE"],
                [],
                200,
                id="Successfully adding '/records/{id_} DELETE' to authorised routes",
            ),
            pytest.param(
                "testuserthatdoesnotexistinthedatabaselocal",
                None,
                [],
                ["/submit/hdf POST"],
                200,
                id="Successfully removed '/submit/hdf POST' from authorised routes",
            ),
            pytest.param(
                "testuserthatdoesnotexistinthedatabaselocal",
                None,
                ["/records/{id_} DELETE", "/users POST"],
                ["/records/{id_} DELETE", "/experiments POST"],
                200,
                id="Successfully adding '/records/{id_} DELETE' and '/users POST' "
                "to authorised routes and removed '/records/{id_} DELETE' and"
                " '/experiments POST'",
            ),
            pytest.param(
                "testuserthatdoesnotexistinthedatabaselocal",
                None,
                ["/records/{id_} DELETE", "/users POST"],
                ["/records/{id_} DELETE", "/experiments POST", "/users POST"],
                200,
                id="Successfully removed everything that was added "
                "as well as '/experiments POST'",
            ),
            pytest.param(
                "",
                "passwords",
                [],
                [],
                500,
                id="Failure username empty",
            ),
            pytest.param(
                None,
                "passwords",
                [],
                [],
                422,
                id="Falure no username",
            ),
            pytest.param(
                "testuserthatdoesnotexistinthedatabaselocal",
                "",
                [],
                [],
                400,
                id="Failure password empty",
            ),
            pytest.param(
                "testuserthatdoesnotexistinthedatabaselocal",
                "",
                ["bad route"],
                [],
                400,
                id="Failure bad add route",
            ),
            pytest.param(
                "testuserthatdoesnotexistinthedatabaselocal",
                "",
                [],
                ["bad route"],
                400,
                id="Failure bad remove route",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_update_local_user(
        self,
        test_app: TestClient,
        login_and_get_token,
        add_delete_local_fixture,
        username,
        updated_password,
        add_authorised_routes,
        remove_authorised_routes,
        expected_response_code,
    ):
        update_local_response = test_app.patch(
            "/users",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
            content=json.dumps(
                {
                    "_id": username,
                    "updated_password": updated_password,
                    "add_authorised_routes": add_authorised_routes,
                    "remove_authorised_routes": remove_authorised_routes,
                },
            ),
        )

        assert update_local_response.status_code == expected_response_code

    @pytest.mark.asyncio
    async def test_update_local_user_forbidden(
        self,
        test_app: TestClient,
        add_delete_local_fixture,
    ):
        update_local_response = test_app.patch(
            "/users",
            content=json.dumps(
                {
                    "_id": "testuserthatdoesnotexistinthedatabaselocal",
                    "updated_password": "passwords",
                    "add_authorised_routes": [],
                    "remove_authorised_routes": [],
                },
            ),
        )

        assert update_local_response.status_code == 403

    @pytest.mark.parametrize(
        "username, updated_password, expected_response_code",
        [
            # ignores password if a FedID user is trying to be changed
            pytest.param(
                "testuserthatdoesnotexistinthedatabasefed",
                "password",
                200,
                id="Failure bad add route",
            ),
            # gives an error if the password field is empty though
            pytest.param(
                "testuserthatdoesnotexistinthedatabasefed",
                "",
                400,
                id="Failure bad remove route",
            ),
            # control to make sure it works without a password field
            pytest.param(
                "testuserthatdoesnotexistinthedatabasefed",
                None,
                200,
                id="Failure bad remove route",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_update_fed_user_password(
        self,
        test_app: TestClient,
        login_and_get_token,
        add_delete_fed_fixture,
        username,
        updated_password,
        expected_response_code,
    ):
        update_fed_response = test_app.patch(
            "/users",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
            content=json.dumps(
                {
                    "_id": username,
                    "updated_password": updated_password,
                },
            ),
        )

        assert update_fed_response.status_code == expected_response_code
