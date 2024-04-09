from bson import ObjectId
from fastapi.testclient import TestClient

from test.endpoints.favourite_filters.conftest import FavouriteFilter


class TestSaveFilter:
    def test_save_filter(
        self,
        test_app: TestClient,
        login_and_get_token,
    ):
        name = "Test Create Filter"
        filter = "PM-201-HJ-CRY-FLOW > 10"

        test_response = test_app.post(
            f"/users/filters?name={name}&filter={filter}",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_response.status_code == 201

        # Testing the response is a valid object ID
        filter_id = test_response.json()
        ObjectId(filter_id)

        test_filter = FavouriteFilter()
        result = test_filter.find_one(filter_id)
        print(f"Result 123: {result}")
        assert result.get("filters") is not None

        test_filter.delete(filter_id)
