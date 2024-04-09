from fastapi.testclient import TestClient


class TestGetFilterList:
    def test_get_filter_list(
        self,
        multiple_favourite_filters,
        test_app: TestClient,
        login_and_get_token,
    ):
        test_response = test_app.get(
            "/users/filters",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_response.status_code == 200
        assert test_response.json() == multiple_favourite_filters
