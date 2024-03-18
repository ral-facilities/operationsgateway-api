import json

from fastapi.testclient import TestClient
import pytest

from operationsgateway_api.src.users.user import User


class TestUpdateUsers:
    @pytest.mark.parametrize(
        "updated_password, add_authorised_routes, "
        "remove_authorised_routes, expected_response_code, expected_routes",
        [
            pytest.param(
                "passwords",
                [],
                [],
                200,
                ["/submit/hdf POST", "/experiments POST"],
                id="Successful local user password update",
            ),
            pytest.param(
                "password",
                [],
                [],
                200,
                ["/submit/hdf POST", "/experiments POST"],
                id="Updating the password to itself",
            ),
            pytest.param(
                None,
                [],
                [],
                200,
                ["/submit/hdf POST", "/experiments POST"],
                id="Successfully updating nothing",
            ),
            pytest.param(
                None,
                None,
                [],
                200,
                ["/submit/hdf POST", "/experiments POST"],
                id="Successfully updating nothing (empty add routes)",
            ),
            pytest.param(
                None,
                [],
                None,
                200,
                ["/submit/hdf POST", "/experiments POST"],
                id="Successfully updating nothing (empty remove routes)",
            ),
            pytest.param(
                None,
                None,
                None,
                200,
                ["/submit/hdf POST", "/experiments POST"],
                id="Successfully updating nothing (empty routes)",
            ),
            pytest.param(
                None,
                ["/records/{id_} DELETE"],
                [],
                200,
                ["/submit/hdf POST", "/experiments POST", "/records/{id_} DELETE"],
                id="Successfully adding '/records/{id_} DELETE' to authorised routes",
            ),
            pytest.param(
                None,
                [],
                ["/submit/hdf POST"],
                200,
                ["/experiments POST"],
                id="Successfully removed '/submit/hdf POST' from authorised routes",
            ),
            pytest.param(
                None,
                ["/records/{id_} DELETE", "/users POST"],
                ["/records/{id_} DELETE", "/experiments POST"],
                200,
                ["/submit/hdf POST", "/users POST"],
                id="Successfully adding '/records/{id_} DELETE' and '/users POST' "
                "to authorised routes and removed '/records/{id_} DELETE' and"
                " '/experiments POST'",
            ),
            pytest.param(
                None,
                ["/records/{id_} DELETE", "/users POST"],
                ["/records/{id_} DELETE", "/experiments POST", "/users POST"],
                200,
                ["/submit/hdf POST"],
                id="Successfully removed everything that was added "
                "as well as '/experiments POST'",
            ),
            pytest.param(
                None,
                ["/records/{id_} DELETE"],
                [
                    "/records/{id_} DELETE",
                    "/experiments POST",
                    "/users POST",
                    "/submit/hdf POST",
                ],
                200,
                [],
                id="Successfully removed everything and attempted to remove more",
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
        expected_routes,
    ):
        username = "testuserthatdoesnotexistinthedatabaselocal"
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
        user = await User.get_user(username)

        if user.sha256_password is not None:
            assert User.hash_password(updated_password) == user.sha256_password

        assert set(user.authorised_routes) == set(expected_routes)

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
            # gives an error if the password field is empty not None for FedID
            pytest.param(
                "testuserthatdoesnotexistinthedatabasefed",
                "",
                None,
                None,
                400,
                id="Failure password exists but is empty",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_update_user_fail(
        self,
        test_app: TestClient,
        login_and_get_token,
        add_delete_local_fixture,
        add_delete_fed_fixture,
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

        if expected_response_code == 200:
            user = await User.get_user(username)
            assert user.sha256_password is None

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
