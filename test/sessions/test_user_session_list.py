from datetime import datetime
from unittest.mock import patch

import pytest

from operationsgateway_api.src.constants import DATA_DATETIME_FORMAT
from operationsgateway_api.src.models import UserSessionListModel
from operationsgateway_api.src.sessions.user_session_list import UserSessionList


class TestUserSessionList:
    def test_init(self):
        test_session_list = UserSessionList("Test User")
        assert test_session_list.username == "Test User"

    @pytest.mark.asyncio
    @patch("operationsgateway_api.src.mongo.interface.MongoDBInterface.find")
    async def test_get_session_list(self, _):
        mock_return_value = []
        for i in range(3):
            mock_return_value.append(
                {
                    "username": "Test User",
                    "name": f"Test User Session {i}",
                    "summary": "Test Summary",
                    "timestamp": datetime.strftime(
                        datetime.now(),
                        DATA_DATETIME_FORMAT,
                    ),
                    "auto_saved": False,
                    "session": {"mySessionData": [1, 2, 3]},
                },
            )

        expected_sessions = [
            UserSessionListModel(**mock_session) for mock_session in mock_return_value
        ]

        with patch(
            "operationsgateway_api.src.mongo.interface.MongoDBInterface.query_to_list",
            return_value=mock_return_value,
        ):
            test_session_list = UserSessionList("Test User")
            sessions = await test_session_list.get_session_list()

            assert sessions == expected_sessions
