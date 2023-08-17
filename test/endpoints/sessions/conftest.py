from datetime import datetime
from typing import Any, Dict

from bson import ObjectId
from pymongo import MongoClient
import pytest

from operationsgateway_api.src.config import Config
from operationsgateway_api.src.exceptions import DatabaseError


@pytest.fixture()
def single_user_session():
    test_session = Session()
    inserted_session = test_session.create()

    yield inserted_session

    test_session.delete(inserted_session["_id"])


@pytest.fixture()
def multiple_user_sessions():
    test_session = Session()
    test_session.delete_all()

    inserted_sessions = test_session.create_multiple()

    yield inserted_sessions

    test_session.delete_all()


class Session:
    def __init__(self) -> None:
        mongo_client = MongoClient(Config.config.mongodb.mongodb_url)
        og_db = mongo_client[Config.config.mongodb.database_name]
        self.sessions = og_db["sessions"]

        self.test_sessions = [
            {
                "username": "backend",
                "name": "Test User Session",
                "summary": "Test Summary",
                "timestamp": "2023-06-01T13:00:00",
                "auto_saved": True,
                "session": {"myData": 123},
            },
            {
                "username": "backend",
                "name": "Test User Session #2",
                "summary": "Test Summary #2",
                "timestamp": "2023-06-01T14:00:00",
                "auto_saved": False,
                "session": {"myData": 456},
            },
        ]

    def count(self):
        return self.sessions.count_documents({})

    def find_one(self, session_id) -> Dict[str, Any]:
        result = self.sessions.find_one({"_id": ObjectId(session_id)})

        if not result:
            return None

        result["_id"] = str(result["_id"])
        if isinstance(result["timestamp"], datetime):
            result["timestamp"] = result["timestamp"].strftime("%Y-%m-%dT%H:%M:%S")
        return result

    def create(self) -> Dict[str, Any]:
        session = self.test_sessions[0]
        self.sessions.insert_one(session).inserted_id

        session["_id"] = str(session["_id"])
        return session

    def create_multiple(self):
        sessions = self.test_sessions
        self.sessions.insert_many(sessions, ordered=True).inserted_ids
        for session in sessions:
            session["_id"] = str(session["_id"])

        return sessions

    def delete(self, session_id: str):
        if self.find_one(session_id):
            result = self.sessions.delete_one({"_id": ObjectId(session_id)})
            if result.deleted_count != 1:
                raise DatabaseError("Test session wasn't deleted")

    def delete_all(self):
        number_of_sessions = self.count()

        result = self.sessions.delete_many({})
        if result.deleted_count != number_of_sessions:
            raise DatabaseError(
                f"Not all sessions were expected. Deleted: {result.deleted_count} but"
                f" expected to delete: {number_of_sessions}",
            )
