from fastapi.testclient import TestClient
import pytest

from operationsgateway_api.src.exceptions import UnauthorisedError
from operationsgateway_api.src.users.user import User


class TestDeleteUsers:
    @pytest.mark.parametrize(
        "username",
        [
            pytest.param(
                "testuserthatdoesnotexistinthedatabasefed",
                id="Delete fed user success",
            ),
            pytest.param(
                "testuserthatdoesnotexistinthedatabaselocal",
                id="Delete local user success",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_delete_user_success(
        self,
        test_app: TestClient,
        login_and_get_token,
        add_delete_local_fixture,
        add_delete_fed_fixture,
        username,
    ):
        delete_local_response = test_app.delete(
            "/users/" + username,
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert delete_local_response.status_code == 204

        try:
            await User.get_user(username)
            pytest.fail("Failed to delete user")
        except UnauthorisedError:
            pass

    @pytest.mark.parametrize(
        "username",
        [
            pytest.param(
                "testuserthatdoesnotexistinthedatabase",
                id="Delete user not exists fail",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_delete_user_fail(
        self,
        test_app: TestClient,
        login_and_get_token,
        username,
    ):
        delete_response = test_app.delete(
            "/users/" + username,
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert delete_response.status_code == 400

        try:
            await User.get_user(username)
            pytest.fail(
                "testuserthatdoesnotexistinthedatabase exists in the database"
                ", need to make sure that isn't a real user",
            )
        except UnauthorisedError:
            pass

    @pytest.mark.parametrize(
        "username",
        [
            pytest.param(
                "testuserthatdoesnotexistinthedatabasefed",
                id="Delete fed user forbidden",
            ),
            pytest.param(
                "testuserthatdoesnotexistinthedatabaselocal",
                id="Delete local user forbidden",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_delete_user_forbidden(
        self,
        test_app: TestClient,
        add_delete_local_fixture,
        add_delete_fed_fixture,
        username,
    ):
        delete_fed_response = test_app.delete(
            "/users/" + username,
        )

        assert delete_fed_response.status_code == 403

        try:
            await User.get_user(username)
        except UnauthorisedError:
            pytest.fail("Test should have been forbidden to delete user")
