import json

from fastapi.testclient import TestClient
import pytest

from operationsgateway_api.src.routes.users import validationHelp
from operationsgateway_api.src.users.user import User


class TestUpdateUsers:
    @pytest.mark.parametrize(
        "updated_password, add_authorised_routes, "
        "remove_authorised_routes, expected_response_code",
        [
            pytest.param(
                "passwords",
                [],
                [],
                200,
                id="Successful local user password update",
            ),
            pytest.param(
                "password",
                [],
                [],
                200,
                id="Updating the password to itself",
            ),
            pytest.param(
                None,
                [],
                [],
                200,
                id="Successfully updating nothing",
            ),
            pytest.param(
                None,
                None,
                [],
                200,
                id="Successfully updating nothing (empty add routes)",
            ),
            pytest.param(
                None,
                [],
                None,
                200,
                id="Successfully updating nothing (empty remove routes)",
            ),
            pytest.param(
                None,
                None,
                None,
                200,
                id="Successfully updating nothing (empty routes)",
            ),
            pytest.param(
                None,
                ["/records/{id_} DELETE"],
                [],
                200,
                id="Successfully adding '/records/{id_} DELETE' to authorised routes",
            ),
            pytest.param(
                None,
                [],
                ["/submit/hdf POST"],
                200,
                id="Successfully removed '/submit/hdf POST' from authorised routes",
            ),
            pytest.param(
                None,
                ["/records/{id_} DELETE", "/users POST"],
                ["/records/{id_} DELETE", "/experiments POST"],
                200,
                id="Successfully adding '/records/{id_} DELETE' and '/users POST' "
                "to authorised routes and removed '/records/{id_} DELETE' and"
                " '/experiments POST'",
            ),
            pytest.param(
                None,
                ["/records/{id_} DELETE", "/users POST"],
                ["/records/{id_} DELETE", "/experiments POST", "/users POST"],
                200,
                id="Successfully removed everything that was added "
                "as well as '/experiments POST'",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_update_user_success(
        self,
        test_app: TestClient,
        login_and_get_token,
        add_delete_local_fixture,
        updated_password,
        add_authorised_routes,
        remove_authorised_routes,
        expected_response_code,
    ):
        username = "testuserthatdoesnotexistinthedatabaselocal"
        before_user = await User.get_user(username)
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
        after_user = await User.get_user(username)
        
        if after_user.sha256_password != None:
            assert validationHelp.hash_password(updated_password) == after_user.sha256_password

        assert update_local_response.status_code == expected_response_code
    
    @pytest.mark.parametrize(
        "username, updated_password, add_authorised_routes, "
        "remove_authorised_routes, expected_response_code",
        [
    pytest.param(
                "",
                "passwords",
                [],
                [],
                400,
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
        ]
    )
    @pytest.mark.asyncio
    async def test_update_user_fail(
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
                id="Success ignore password on fed user",
            ),
            # gives an error if the password field is empty though
            pytest.param(
                "testuserthatdoesnotexistinthedatabasefed",
                "",
                400,
                id="Failure password exists but is empty",
            ),
            # control to make sure it works without a password field
            pytest.param(
                "testuserthatdoesnotexistinthedatabasefed",
                None,
                200,
                id="Success no password",
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
