from bson import ObjectId
from fastapi.testclient import TestClient
import pytest

from test.endpoints.favourite_filters.conftest import FavouriteFilter


class TestUpdateFilter:
    @pytest.mark.parametrize(
        "updated_name, updated_filter, expected_name, expected_filter",
        [
            pytest.param(
                "Test Update Filter",
                "PM-201-HJ-CRY-FLOW > 20",
                "Test Update Filter",
                "PM-201-HJ-CRY-FLOW > 20",
                id="Update name and filter",
            ),
            pytest.param(
                "Test Update Filter, name only",
                None,
                "Test Update Filter, name only",
                "PM-201-HJ-CRY-T > PM-201-HJ-CRY-FLOW",
                id="Update name only",
            ),
            pytest.param(
                None,
                "PM-201-HJ-CRY-FLOW > 30",
                "Test Filter #1",
                "PM-201-HJ-CRY-FLOW > 30",
                id="Update filter only",
            ),
            pytest.param(
                None,
                None,
                "Test Filter #1",
                "PM-201-HJ-CRY-T > PM-201-HJ-CRY-FLOW",
                id="No updates",
            ),
        ],
    )
    def test_update_filter(
        self,
        single_favourite_filter,
        test_app: TestClient,
        login_and_get_token,
        updated_name,
        updated_filter,
        expected_name,
        expected_filter,
    ):
        query_params = []
        if updated_name is not None:
            query_params.append(f"name={updated_name}")
        if updated_filter is not None:
            query_params.append(f"filter={updated_filter}")

        query_params_str = "&".join(query_params)
        question_mark = "?" if query_params_str else ""

        test_response = test_app.patch(
            f"/users/filters/{single_favourite_filter['_id']}{question_mark}{query_params_str}",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_response.status_code == 200
        if updated_name is None and updated_filter is None:
            assert test_response.json() == "No updates necessary"
        else:
            assert test_response.json() == f"Updated {single_favourite_filter['_id']}"

        test_filter = FavouriteFilter()
        filter_update = test_filter.find_one(single_favourite_filter["_id"])

        expected_filter = {
            "_id": ObjectId(single_favourite_filter["_id"]),
            "name": expected_name,
            "filter": expected_filter,
        }

        assert filter_update["filters"][0] == expected_filter
