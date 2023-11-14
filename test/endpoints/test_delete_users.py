from fastapi.testclient import TestClient
import pytest


class TestDeleteUsers:
    @pytest.mark.parametrize(
        "username",
        [
            pytest.param(
                "/users/testuserthatdoesnotexistinthedatabasefed",
                id="Delete fed user success",
            ),
            pytest.param(
                "/users/testuserthatdoesnotexistinthedatabaselocal",
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
            username,
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert delete_local_response.status_code == 204

    @pytest.mark.parametrize(
        "username",
        [
            pytest.param(
                "/users/testuserthatdoesnotexistinthedatabase",
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
            username,
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert delete_response.status_code == 500

    @pytest.mark.parametrize(
        "username",
        [
            pytest.param(
                "/users/testuserthatdoesnotexistinthedatabasefed",
                id="Delete fed user forbidden",
            ),
            pytest.param(
                "/users/testuserthatdoesnotexistinthedatabaselocal",
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
            username,
        )

        assert delete_fed_response.status_code == 403
