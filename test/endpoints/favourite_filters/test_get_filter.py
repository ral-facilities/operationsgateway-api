from fastapi.testclient import TestClient


class TestGetFilter:
    def test_get_filter(
        self,
        single_favourite_filter,
        test_app: TestClient,
        login_and_get_token,
    ):
        test_response = test_app.get(
            f"/users/filters/{single_favourite_filter['_id']}",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_response.status_code == 200
        assert test_response.json() == single_favourite_filter
