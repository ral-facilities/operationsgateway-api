from bson import ObjectId
from fastapi.testclient import TestClient
import pytest

from test.endpoints.favourite_filters.conftest import FavouriteFilter


class TestSaveFilter:
    def test_save_filter(
        self,
        test_app: TestClient,
        login_and_get_token,
    ):
        name = "Test Create Filter"
        filter_content = "PM-201-HJ-CRY-FLOW > 10"

        test_response = test_app.post(
            f"/users/filters?name={name}&filter={filter_content}",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_response.status_code == 201

        # Testing the response is a valid object ID
        filter_id = test_response.json()
        ObjectId(filter_id)

        test_filter = FavouriteFilter()
        result = test_filter.find_one(filter_id)
        try:
            assert len(result.get("filters")) == 1
            assert "_id" in result.get("filters")[0]
            assert result.get("filters")[0]["name"] == "Test Create Filter"
            assert result.get("filters")[0]["filter"] == "PM-201-HJ-CRY-FLOW > 10"
        finally:
            # A fixture cannot be used as the filter_id will change each time
            test_filter.delete(filter_id)

    @pytest.mark.parametrize(
        "name, filter_content",
        [
            pytest.param("", "PM-201-HJ-CRY-FLOW > 10", id="Empty name"),
            pytest.param("Test Create Invalid Filter", "", id="Empty filter"),
        ],
    )
    def test_invalid_save_filter(
        self,
        test_app: TestClient,
        login_and_get_token,
        name,
        filter_content,
    ):
        test_response = test_app.post(
            f"/users/filters?name={name}&filter={filter_content}",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_response.status_code == 400
