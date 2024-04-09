from bson import ObjectId
from fastapi.testclient import TestClient

from test.endpoints.favourite_filters.conftest import FavouriteFilter



class TestUpdateFilter:
    def test_update_filter(
        self,
        single_favourite_filter,
        test_app: TestClient,
        login_and_get_token,
    ):
        updated_name = "Test Update Filter"
        updated_filter = "PM-201-HJ-CRY-FLOW > 20"

        test_response = test_app.patch(
            f"/users/filters/{single_favourite_filter['_id']}?name={updated_name}"
            f"&filter={updated_filter}",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_response.status_code == 200
        assert test_response.json() == f"Updated {single_favourite_filter['_id']}"

        test_filter = FavouriteFilter()
        filter_update = test_filter.find_one(single_favourite_filter["_id"])

        expected_filter = {
            "_id": ObjectId(single_favourite_filter["_id"]),
            "name": updated_name,
            "filter": updated_filter,
        }

        assert filter_update["filters"][0] == expected_filter
