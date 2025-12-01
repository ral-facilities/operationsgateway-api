import json
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
import pytest
import pytest_asyncio

from operationsgateway_api.src.auth.authentication import Authentication
from operationsgateway_api.src.exceptions import UnauthorisedError
from operationsgateway_api.src.models import UserModel
from operationsgateway_api.src.users.user import User


class TestCreateUsers:

    @staticmethod
    @pytest_asyncio.fixture()
    async def mock_fedid_email(monkeypatch):
        monkeypatch.setattr(
            "operationsgateway_api.src.routes.users.Authentication.get_email_from_fedid",
            staticmethod(lambda username: "test@example.com"),
        )

    @staticmethod
    @pytest_asyncio.fixture()
    async def mock_fedid_email_none(monkeypatch):
        monkeypatch.setattr(
            Authentication,
            "get_email_from_fedid",
            lambda _: None,
        )

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
                "testuserthatdoesnotexistinthedatabasefed",
                "FedID",
                None,
                None,
                201,
                id="Successful fed user creation no paths",
            ),
            pytest.param(
                "testuserthatdoesnotexistinthedatabasefed",
                "FedID",
                [],
                None,
                201,
                id="Successful fed user creation empty paths",
            ),
            pytest.param(
                "testuserthatdoesnotexistinthedatabasefed",
                "FedID",
                ["/submit/hdf POST"],
                None,
                201,
                id="Successful fed user creation with paths",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_create_user_success(
        self,
        test_app: TestClient,
        login_and_get_token,
        delete_local_fixture,
        delete_fed_fixture,
        username,
        auth_type,
        routes,
        password,
        expected_response_code,
        mock_fedid_email,
    ):
        create_response = test_app.post(
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

        assert create_response.status_code == expected_response_code

        assert create_response.text[1:-1] == username

        user = await User.get_user(username)
        assert username == user.username
        assert auth_type == user.auth_type
        assert routes == user.authorised_routes
        if password is not None:
            assert User.hash_password(password) == user.sha256_password

    @pytest.mark.parametrize(
        "username, auth_type, routes, password, expected_response_code",
        [
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
            pytest.param(
                "",
                "FedID",
                None,
                None,
                400,
                id="Failed fed user creation blank username",
            ),
            pytest.param(
                None,
                "FedID",
                None,
                None,
                422,
                id="failed fed user creation no username",
            ),
            pytest.param(
                "testuserthatdoesnotexistinthedatabasefed",
                "FedID",
                ["/submit/hdf POST", "false path"],
                None,
                400,
                id="Failed fed user creation logs 'false path' to console",
            ),
            pytest.param(
                "testuserthatdoesnotexistinthedatabasefed",
                "FedID",
                ["false path"],
                None,
                400,
                id="Failed fed user creation logs 'false path' to console (pure)",
            ),
            pytest.param(
                "testuserthatdoesnotexistinthedatabasefed",
                "bad auth_type",
                None,
                None,
                400,
                id="Failed user creation because of bad auth_type",
            ),
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
                "password",
                400,
                id="Failed fed user creation with password",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_create_user_fail(
        self,
        test_app: TestClient,
        login_and_get_token,
        delete_local_fixture,
        delete_fed_fixture,
        username,
        auth_type,
        routes,
        password,
        expected_response_code,
    ):
        create_response = test_app.post(
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

        assert create_response.status_code == expected_response_code

    @pytest.mark.parametrize(
        "username, auth_type, routes, password, expected_response_code",
        [
            pytest.param(
                "testuserthatdoesnotexistinthedatabasefed",
                "FedID",
                ["/submit/hdf POST", "/experiments POST"],
                None,
                401,
                id="Failed fed user creation blank password",
            ),
            pytest.param(
                "testuserthatdoesnotexistinthedatabaselocal",
                "local",
                ["/submit/hdf POST", "/experiments POST"],
                "password",
                401,
                id="Failed fed user creation blank password",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_create_fed_user_forbidden(
        self,
        test_app: TestClient,
        add_delete_fed_fixture,
        username,
        auth_type,
        routes,
        password,
        expected_response_code,
    ):
        create_response = test_app.post(
            "/users",
            content=json.dumps(
                {
                    "_id": username,
                    "auth_type": auth_type,
                    "authorised_routes": routes,
                    "sha256_password": password,
                },
            ),
        )

        assert create_response.status_code == expected_response_code

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

    @pytest.mark.asyncio
    async def test_fedid_user_creation_fails_without_email(
        self,
        test_app: TestClient,
        login_and_get_token,
        delete_fed_fixture,
        mock_fedid_email_none,
    ):
        response = test_app.post(
            "/users",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
            content=json.dumps(
                {
                    "_id": "fed",
                    "auth_type": "FedID",
                    "authorised_routes": ["/submit/hdf POST"],
                },
            ),
        )

        assert response.status_code == 400
        assert "No email found for FedID username 'fed'" in response.text

    @pytest.mark.asyncio
    async def test_user_email_found(self):
        expected_user = {
            "_id": "fed",
            "email": "test@example.com",
            "auth_type": "local",
        }

        with patch(
            "operationsgateway_api.src.mongo.interface.MongoDBInterface.find_one",
            new_callable=AsyncMock,
        ) as mock_find_one:
            mock_find_one.return_value = expected_user

            result = await User.get_user_by_email("test@example.com")

            assert isinstance(result, UserModel)
            assert result.username == "fed"
            assert result.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_user_email_not_found(self):
        with patch(
            "operationsgateway_api.src.mongo.interface.MongoDBInterface.find_one",
            new_callable=AsyncMock,
        ) as mock_find_one:
            mock_find_one.return_value = None

            with pytest.raises(UnauthorisedError):
                await User.get_user_by_email("test@example.com")
