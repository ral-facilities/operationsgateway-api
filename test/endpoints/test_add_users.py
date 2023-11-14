import json

from fastapi.testclient import TestClient
import pytest


class TestCreateUsers:
    @pytest.mark.parametrize(
        "username, auth_type, routes, password, expected_response_code",
        [
            pytest.param(
                "testuserthatdoesnotexistinthedatabaselocal",
                "local",
                None,
                "password",
                201,
                id="Successful local user creation no paths",
            ),
            pytest.param(
                "testuserthatdoesnotexistinthedatabaselocal",
                "local",
                [],
                "password",
                201,
                id="Successful local user creation empty paths",
            ),
            pytest.param(
                "testuserthatdoesnotexistinthedatabaselocal",
                "local",
                ["/submit/hdf POST"],
                "password",
                201,
                id="Successful local user creation with paths",
            ),
            pytest.param(
                "testuserthatdoesnotexistinthedatabaselocal",
                "local",
                None,
                "",
                400,
                id="Failed local user creation blank password",
            ),
            pytest.param(
                "testuserthatdoesnotexistinthedatabaselocal",
                "local",
                None,
                None,
                400,
                id="Failed local user creation no password",
            ),
            pytest.param(
                "",
                "local",
                None,
                "password",
                400,
                id="Failed local user creation blank username",
            ),
            pytest.param(
                None,
                "local",
                None,
                "password",
                422,
                id="Failed local user creation no username",
            ),
            pytest.param(
                "testuserthatdoesnotexistinthedatabaselocal",
                "",
                None,
                "password",
                400,
                id="Failed local user creation blank auth_type",
            ),
            pytest.param(
                "testuserthatdoesnotexistinthedatabaselocal",
                None,
                None,
                "password",
                422,
                id="failed local user creation no auth_type",
            ),
            pytest.param(
                "testuserthatdoesnotexistinthedatabaselocal",
                "local",
                ["/submit/hdf POST", "false path"],
                "password",
                400,
                id="Failed local user creation logs 'false path' to console",
            ),
            pytest.param(
                "testuserthatdoesnotexistinthedatabaselocal",
                "local",
                ["false path"],
                "password",
                400,
                id="Failed local user creation logs 'false path' to console (pure)",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_create_local_user(
        self,
        test_app: TestClient,
        login_and_get_token,
        delete_local_fixture,
        username,
        auth_type,
        routes,
        password,
        expected_response_code,
    ):
        create_local_response = test_app.post(
            "/users",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
            content=json.dumps(
                {
                    "_id": username,
                    "auth_type": auth_type,
                    "authorised_routes": routes,
                    "sha256_password": password,
                },
            ),
        )

        assert create_local_response.status_code == expected_response_code

    @pytest.mark.asyncio
    async def test_create_preexisting_local_user(
        self,
        test_app: TestClient,
        login_and_get_token,
        add_delete_local_fixture,
    ):
        create_local_response = test_app.post(
            "/users",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
            content=json.dumps(
                {
                    "_id": "testuserthatdoesnotexistinthedatabaselocal",
                    "auth_type": "local",
                    "authorised_routes": ["/submit/hdf POST", "/experiments POST"],
                    "sha256_password": "password",
                },
            ),
        )

        assert create_local_response.status_code == 400

    @pytest.mark.parametrize(
        "username, auth_type, routes, expected_response_code",
        [
            pytest.param(
                "testuserthatdoesnotexistinthedatabasefed",
                "FedID",
                None,
                201,
                id="Successful fed user creation no paths",
            ),
            pytest.param(
                "testuserthatdoesnotexistinthedatabasefed",
                "FedID",
                [],
                201,
                id="Successful fed user creation empty paths",
            ),
            pytest.param(
                "testuserthatdoesnotexistinthedatabasefed",
                "FedID",
                ["/submit/hdf POST"],
                201,
                id="Successful fed user creation with paths",
            ),
            pytest.param(
                "",
                "FedID",
                None,
                400,
                id="Failed fed user creation blank username",
            ),
            pytest.param(
                None,
                "FedID",
                None,
                422,
                id="failed fed user creation no username",
            ),
            pytest.param(
                "testuserthatdoesnotexistinthedatabasefed",
                "FedID",
                ["/submit/hdf POST", "false path"],
                400,
                id="Failed fed user creation logs 'false path' to console",
            ),
            pytest.param(
                "testuserthatdoesnotexistinthedatabasefed",
                "FedID",
                ["false path"],
                400,
                id="Failed fed user creation logs 'false path' to console (pure)",
            ),
            pytest.param(
                "testuserthatdoesnotexistinthedatabasefed",
                "bad auth_type",
                None,
                400,
                id="Failed user creation because of bad auth_type",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_create_fed_user(
        self,
        test_app: TestClient,
        login_and_get_token,
        delete_fed_fixture,
        username,
        auth_type,
        routes,
        expected_response_code,
    ):
        create_fed_response = test_app.post(
            "/users",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
            content=json.dumps(
                {
                    "_id": username,
                    "auth_type": auth_type,
                    "authorised_routes": routes,
                },
            ),
        )

        assert create_fed_response.status_code == expected_response_code

        if expected_response_code == 201:
            assert create_fed_response.text[1:-1] == username

    @pytest.mark.parametrize(
        "username, auth_type, routes, password, expected_response_code",
        [
            pytest.param(
                "testuserthatdoesnotexistinthedatabasefed",
                "FedID",
                None,
                "",
                400,
                id="Failed fed user creation blank password",
            ),
            pytest.param(
                "testuserthatdoesnotexistinthedatabasefed",
                "FedID",
                None,
                None,
                201,
                id="Successful fed user creation no password",
            ),
            pytest.param(
                "testuserthatdoesnotexistinthedatabasefed",
                "FedID",
                None,
                "password",
                400,
                id="Failed fed user creation with password",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_password_fed_user(
        self,
        test_app: TestClient,
        login_and_get_token,
        delete_fed_fixture,
        username,
        auth_type,
        routes,
        password,
        expected_response_code,
    ):
        create_fed_response = test_app.post(
            "/users",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
            content=json.dumps(
                {
                    "_id": username,
                    "auth_type": auth_type,
                    "authorised_routes": routes,
                    "sha256_password": password,
                },
            ),
        )

        assert create_fed_response.status_code == expected_response_code

        if expected_response_code == 201:
            assert create_fed_response.text[1:-1] == username

    @pytest.mark.asyncio
    async def test_create_local_user_forbidden(
        self,
        test_app: TestClient,
        add_delete_local_fixture,
    ):
        create_local_response = test_app.post(
            "/users",
            content=json.dumps(
                {
                    "_id": "testuserthatdoesnotexistinthedatabaselocal",
                    "auth_type": "local",
                    "authorised_routes": ["/submit/hdf POST", "/experiments POST"],
                    "sha256_password": "password",
                },
            ),
        )

        assert create_local_response.status_code == 403

    @pytest.mark.asyncio
    async def test_create_fed_user_forbidden(
        self,
        test_app: TestClient,
        add_delete_fed_fixture,
    ):
        create_fed_response = test_app.post(
            "/users",
            content=json.dumps(
                {
                    "_id": "testuserthatdoesnotexistinthedatabasefed",
                    "auth_type": "FedID",
                    "authorised_routes": ["/submit/hdf POST", "/experiments POST"],
                },
            ),
        )

        assert create_fed_response.status_code == 403
