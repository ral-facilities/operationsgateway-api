from datetime import datetime
from unittest.mock import patch

from bson import ObjectId
from pymongo.errors import DuplicateKeyError
import pytest

from operationsgateway_api.src.auth.jwt_handler import JwtHandler
from operationsgateway_api.src.constants import DATA_DATETIME_FORMAT
from operationsgateway_api.src.exceptions import (
    DatabaseError,
    DuplicateSessionError,
    ForbiddenError,
    MissingDocumentError,
    ModelError,
)
from operationsgateway_api.src.models import UserModel, UserSessionModel
from operationsgateway_api.src.sessions.user_session import UserSession
from test.mock_models import (
    MockDeleteResult,
    MockInsertOneResult,
    MockUpdateResult,
)


class TestUserSession:
    session_data_dict = {
        "_id": ObjectId("646cdd9da393909af29784f0"),
        "username": "Test User",
        "name": "Test Session",
        "summary": "Test Summary",
        "timestamp": datetime.strftime(datetime.now(), DATA_DATETIME_FORMAT),
        "auto_saved": False,
        "session": {"sessionData": [1, 2, 3]},
    }

    def test_init(self):
        session_model = UserSessionModel(**TestUserSession.session_data_dict)
        test_session = UserSession(session_model)
        assert test_session.session == session_model

    @pytest.mark.asyncio
    async def test_valid_get(self):
        mock_database_return = {
            "_id": ObjectId("646cdd9da393909af29784f0"),
            "username": "Test User",
            "name": "Test Session",
            "summary": "Test Summary",
            "timestamp": datetime.strftime(datetime.now(), DATA_DATETIME_FORMAT),
            "auto_saved": False,
            "session": {"sessionData": [1, 2, 3]},
        }

        with patch(
            "operationsgateway_api.src.mongo.interface.MongoDBInterface.find_one",
            return_value=mock_database_return,
        ):
            test_session = await UserSession.get("646cdd9da393909af29784f0")
            expected_session = UserSessionModel(**mock_database_return)
            assert test_session == expected_session

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "mock_database_return, input_id, expected_exception",
        [
            pytest.param(None, "Invalid Object ID", ModelError, id="Invalid ObjectId"),
            pytest.param(
                {"_id": ObjectId("646cdd9da393909af29784f0"), "name": "Test Session"},
                "646cdd9da393909af29784f0",
                ModelError,
                id="Session doesn't fit UserSessionModel",
            ),
            pytest.param(
                None,
                "646cdd9da393909af29784f0",
                MissingDocumentError,
                id="No session found",
            ),
        ],
    )
    async def test_invalid_get(
        self,
        mock_database_return,
        input_id,
        expected_exception,
    ):
        with patch(
            "operationsgateway_api.src.mongo.interface.MongoDBInterface.find_one",
            return_value=mock_database_return,
        ):
            with pytest.raises(expected_exception):
                await UserSession.get(input_id)

    @pytest.mark.asyncio
    @patch(
        "operationsgateway_api.src.mongo.interface.MongoDBInterface.delete_one",
        return_value=MockDeleteResult(acknowledged=True, deleted_count=1),
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.auth.access_token_validity_mins",
        10,
    )
    @patch(
        "operationsgateway_api.src.sessions.user_session.UserSession.get",
        return_value=UserSessionModel(**session_data_dict),
    )
    async def test_valid_delete(self, _, __):
        test_user = UserModel(_id="Test User", auth_type="Test")
        jwt_handler = JwtHandler(test_user)
        access_token = jwt_handler.get_access_token()

        delete_count = await UserSession.delete(
            "646cdd9da393909af29784f0",
            access_token,
        )
        assert delete_count == 1

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "expected_exception, client_username, input_id, expected_deleted_count",
        [
            pytest.param(
                ForbiddenError,
                "Test User #2",
                "646cdd9da393909af29784f0",
                0,
                id="Client username and session username doesn't match",
            ),
            pytest.param(
                ModelError,
                "Test User",
                "Invalid Object ID",
                0,
                id="Invalid ObjectId",
            ),
            pytest.param(
                DatabaseError,
                "Test User",
                "646cdd9da393909af29784f0",
                0,
                id="Unexpected deleted count (< 1)",
            ),
            pytest.param(
                DatabaseError,
                "Test User",
                "646cdd9da393909af29784f0",
                2,
                id="Unexpected deleted count (> 1)",
            ),
        ],
    )
    @patch(
        "operationsgateway_api.src.sessions.user_session.UserSession.get",
        return_value=UserSessionModel(**session_data_dict),
    )
    async def test_invalid_delete(
        self,
        _,
        expected_exception,
        client_username,
        input_id,
        expected_deleted_count,
    ):
        test_user = UserModel(_id=client_username, auth_type="Test")
        jwt_handler = JwtHandler(test_user)
        access_token = jwt_handler.get_access_token()

        with pytest.raises(expected_exception):
            with patch(
                "operationsgateway_api.src.mongo.interface.MongoDBInterface.delete_one",
                return_value=MockDeleteResult(
                    acknowledged=True,
                    deleted_count=expected_deleted_count,
                ),
            ):
                await UserSession.delete(input_id, access_token)

    @pytest.mark.asyncio
    @patch(
        "operationsgateway_api.src.mongo.interface.MongoDBInterface.update_one",
        return_value=MockUpdateResult(
            acknowledged=True,
            matched_count=1,
            modified_count=1,
        ),
    )
    async def test_valid_update(self, mock_database_update):
        test_user = UserModel(_id="Test User", auth_type="Test")
        jwt_handler = JwtHandler(test_user)
        access_token = jwt_handler.get_access_token()

        session_model = UserSessionModel(**TestUserSession.session_data_dict)
        test_session = UserSession(session_model)

        await test_session.update(access_token)

        assert mock_database_update.call_count == 1

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "expected_exception, client_username, mock_update_result",
        [
            pytest.param(
                ForbiddenError,
                "Test User #2",
                None,
                id="Client username and session username doesn't match",
            ),
            pytest.param(
                MissingDocumentError,
                "Test User",
                MockUpdateResult(acknowledged=True, matched_count=0, modified_count=0),
                id="Unexpected matched count (< 1)",
            ),
            pytest.param(
                MissingDocumentError,
                "Test User",
                MockUpdateResult(acknowledged=True, matched_count=2, modified_count=2),
                id="Unexpected matched count (> 1)",
            ),
            pytest.param(
                DatabaseError,
                "Test User",
                MockUpdateResult(acknowledged=True, matched_count=1, modified_count=0),
                id="Unexpected modified count (< 1)",
            ),
            pytest.param(
                DatabaseError,
                "Test User",
                MockUpdateResult(acknowledged=True, matched_count=1, modified_count=5),
                id="Unexpected modified count (> 1)",
            ),
        ],
    )
    async def test_invalid_update(
        self,
        expected_exception,
        client_username,
        mock_update_result,
    ):
        test_user = UserModel(_id=client_username, auth_type="Test")
        jwt_handler = JwtHandler(test_user)
        access_token = jwt_handler.get_access_token()

        session_model = UserSessionModel(**TestUserSession.session_data_dict)
        test_session = UserSession(session_model)

        with pytest.raises(expected_exception):
            with patch(
                "operationsgateway_api.src.mongo.interface.MongoDBInterface.update_one",
                return_value=mock_update_result,
            ):
                await test_session.update(access_token)

    @pytest.mark.asyncio
    @patch(
        "operationsgateway_api.src.mongo.interface.MongoDBInterface.insert_one",
        return_value=MockInsertOneResult(
            acknowledged=True,
            inserted_id="646cdd9da393909af29784f0",
        ),
    )
    async def test_insert(self, _):
        session_model = UserSessionModel(**TestUserSession.session_data_dict)
        test_session = UserSession(session_model)

        inserted_id = await test_session.insert()

        assert inserted_id == "646cdd9da393909af29784f0"

    @pytest.mark.parametrize(
        "session_username, expected_result",
        [
            pytest.param("Test User", True, id="User authorised"),
            pytest.param("Test User #2", False, id="User not authorised"),
        ],
    )
    def test_is_user_authorised(self, session_username, expected_result):
        test_user = UserModel(_id="Test User", auth_type="Test")
        jwt_handler = JwtHandler(test_user)
        access_token = jwt_handler.get_access_token()

        authorised = UserSession._is_user_authorised(access_token, session_username)
        assert authorised == expected_result

    @patch(
        "operationsgateway_api.src.mongo.interface.MongoDBInterface.get_collection_object")
    @pytest.mark.asyncio
    async def test_insert_duplicate_session_name(self, mock_get_collection):
        # Mock the insert_one method on the collection object
        mock_collection = mock_get_collection.return_value
        mock_collection.insert_one.side_effect = DuplicateKeyError(
            "E11000 duplicate key error collection: opsgateway.sessions index: "
            "username_1_name_1 dup key: "
            "{ username: \"Test User\", name: \"Test Session\" }"
        )

        session_model = UserSessionModel(**TestUserSession.session_data_dict)
        test_session = UserSession(session_model)

        with pytest.raises(DuplicateSessionError) as exc_info:
            await test_session.insert()

        assert "Session name already exists" in str(exc_info.value)
