from unittest.mock import patch

from bson import ObjectId
import pytest

from operationsgateway_api.src.exceptions import (
    DatabaseError,
    MissingDocumentError,
    ModelError,
    UserError,
)
from operationsgateway_api.src.models import FavouriteFilterModel
from operationsgateway_api.src.users.favourite_filter import (
    FavouriteFilter,
    FilterCRUDOperation,
)
from test.mock_models import MockUpdateResult


class TestFavouriteFilter:
    def test_valid_init(self):
        test_filter = FavouriteFilter(
            "backend",
            "Test Filter",
            "channel 1 < channel 2",
            "66055ee49dc258bbfd26bbfc",
        )

        assert test_filter.filter_id == ObjectId("66055ee49dc258bbfd26bbfc")
        assert test_filter.filter == {
            "_id": ObjectId("66055ee49dc258bbfd26bbfc"),
            "name": "Test Filter",
            "filter": "channel 1 < channel 2",
        }
        assert test_filter.username == "backend"

    def test_invalid_init(self):
        with pytest.raises(UserError):
            FavouriteFilter(
                "backend",
                "Test Filter",
                "channel 1 < channel 2",
                "my object id",
            )

    @patch("operationsgateway_api.src.mongo.interface.MongoDBInterface.find_one")
    @pytest.mark.asyncio
    async def test_valid_get_list(self, mock_find_one):
        mock_find_one.return_value = {
            "_id": "test_user",
            "filters": [
                {
                    "_id": ObjectId("65e89014ded53893a95fb56b"),
                    "name": "Test Filter 1",
                    "filter": "channel 1 > channel 2",
                },
                {
                    "_id": ObjectId("65e89014ded53893a95fb56d"),
                    "name": "Test Filter 2",
                    "filter": "channel 2 > channel 3",
                },
            ],
        }
        filter_list = await FavouriteFilter.get_list("test_user")

        assert filter_list == [
            FavouriteFilterModel(
                _id=ObjectId("65e89014ded53893a95fb56b"),
                name="Test Filter 1",
                filter="channel 1 > channel 2",
            ),
            FavouriteFilterModel(
                _id=ObjectId("65e89014ded53893a95fb56d"),
                name="Test Filter 2",
                filter="channel 2 > channel 3",
            ),
        ]

    @patch(
        "operationsgateway_api.src.mongo.interface.MongoDBInterface.find_one",
        return_value={"filters": [{"invalid": "filter"}]},
    )
    @pytest.mark.asyncio
    async def test_invalid_get_list(self, _):
        with pytest.raises(ModelError):
            await FavouriteFilter.get_list("test_user")

    @patch("operationsgateway_api.src.mongo.interface.MongoDBInterface.find_one")
    @pytest.mark.asyncio
    async def test_valid_get_by_id(self, mock_find_one):
        mock_find_one.return_value = {
            "_id": "test_user",
            "filters": [
                {
                    "_id": ObjectId("65e89014ded53893a95fb56d"),
                    "name": "Test Filter 2",
                    "filter": "channel 2 > channel 3",
                },
            ],
        }

        test_filter = await FavouriteFilter.get_by_id(
            "test_user",
            "65e89014ded53893a95fb56d",
        )
        assert test_filter == FavouriteFilterModel(
            _id=ObjectId("65e89014ded53893a95fb56d"),
            name="Test Filter 2",
            filter="channel 2 > channel 3",
        )

    @pytest.mark.asyncio
    async def test_invalid_get_by_id(self):
        with pytest.raises(ModelError):
            await FavouriteFilter.get_by_id("test_user", "invalid id")

    @patch(
        "operationsgateway_api.src.mongo.interface.MongoDBInterface.update_one",
        return_value=MockUpdateResult(
            acknowledged=True,
            matched_count=1,
            modified_count=1,
        ),
    )
    @pytest.mark.asyncio
    async def test_valid_delete(self, mock_update_one):
        await FavouriteFilter.delete("test_user", None)
        assert mock_update_one.call_count == 1

    @pytest.mark.asyncio
    async def test_invalid_delete(self):
        with pytest.raises(ModelError):
            await FavouriteFilter.delete("test_user", "invalid id")

    @pytest.mark.parametrize(
        "update_result",
        [
            pytest.param(
                MockUpdateResult(
                    acknowledged=True,
                    matched_count=0,
                    modified_count=0,
                ),
                id="No match",
            ),
            pytest.param(
                MockUpdateResult(
                    acknowledged=True,
                    matched_count=1,
                    modified_count=0,
                ),
                id="No modification",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_invalid_create(self, update_result):
        with patch(
            "operationsgateway_api.src.mongo.interface.MongoDBInterface.update_one",
            return_value=update_result,
        ):

            test_filter = FavouriteFilter(
                "backend",
                "Test Filter",
                "channel 1 < channel 2",
                "66055ee49dc258bbfd26bbfc",
            )
            with pytest.raises(DatabaseError):
                await test_filter.create()

    @pytest.mark.parametrize(
        "update_result, expected_exception",
        [
            pytest.param(
                MockUpdateResult(
                    acknowledged=True,
                    matched_count=0,
                    modified_count=0,
                ),
                MissingDocumentError,
                id="No match",
            ),
            pytest.param(
                MockUpdateResult(
                    acknowledged=True,
                    matched_count=1,
                    modified_count=0,
                ),
                DatabaseError,
                id="No modification",
            ),
        ],
    )
    def test_process_update_result(self, update_result, expected_exception):
        with pytest.raises(expected_exception):
            FavouriteFilter._process_update_result(
                update_result,
                "test_user",
                "65e89014ded53893a95fb56d",
                FilterCRUDOperation.UPDATE,
            )
