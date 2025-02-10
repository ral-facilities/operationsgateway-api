import json
import tempfile
from unittest.mock import patch

from fastapi.testclient import TestClient


class TestMaintenance:
    """
    Both test combine the GET and POST requests in order to test the cache is cleared
    after POSTing a new message.
    """

    def test_maintenance(self, test_app: TestClient, login_and_get_token: str):
        initial_content = {"show": False, "message": ""}
        updated_content = {"show": True, "message": "message"}
        target = "operationsgateway_api.src.config.Config.config.app.maintenance_file"
        tmp_file = tempfile.NamedTemporaryFile()
        with patch(target, tmp_file.name):
            # POST the initial contents (we are using a tmpfile, which will start empty)
            response = test_app.post(
                url="/maintenance",
                content=json.dumps(initial_content),
                headers={"Authorization": f"Bearer {login_and_get_token}"},
            )
            assert response.status_code == 200
            assert json.loads(response.content) is None
            assert json.load(tmp_file) == initial_content
            tmp_file.seek(0)  # Reset so we can read again later

            # Calling GET will save the return value to cache
            response = test_app.get(
                url="/maintenance",
                headers={"Authorization": f"Bearer {login_and_get_token}"},
            )
            assert response.status_code == 200
            assert json.loads(response.content) == initial_content

            # Calling POST will clear the cache after writing to file
            response = test_app.post(
                url="/maintenance",
                content=json.dumps(updated_content),
                headers={"Authorization": f"Bearer {login_and_get_token}"},
            )
            assert response.status_code == 200
            assert json.loads(response.content) is None
            assert json.load(tmp_file) == updated_content

            # Cache has been cleared so should get the new message back
            response = test_app.get(
                url="/maintenance",
                headers={"Authorization": f"Bearer {login_and_get_token}"},
            )
            assert response.status_code == 200
            assert json.loads(response.content) == updated_content

    def test_scheduled_maintenance(
        self,
        test_app: TestClient,
        login_and_get_token: str,
    ):
        initial_content = {"show": False, "message": "", "severity": "info"}
        updated_content = {"show": True, "message": "message", "severity": "warning"}
        target = (
            "operationsgateway_api.src.config.Config.config.app."
            "scheduled_maintenance_file"
        )
        tmp_file = tempfile.NamedTemporaryFile()
        with patch(target, tmp_file.name):
            # POST the initial contents (we are using a tmpfile, which will start empty)
            response = test_app.post(
                url="/maintenance/scheduled",
                content=json.dumps(initial_content),
                headers={"Authorization": f"Bearer {login_and_get_token}"},
            )
            assert response.status_code == 200
            assert json.loads(response.content) is None
            assert json.load(tmp_file) == initial_content
            tmp_file.seek(0)  # Reset so we can read again later

            # Calling GET will save the return value to cache
            response = test_app.get(
                url="/maintenance/scheduled",
                headers={"Authorization": f"Bearer {login_and_get_token}"},
            )
            assert response.status_code == 200
            assert json.loads(response.content) == initial_content

            # Calling POST will clear the cache after writing to file
            response = test_app.post(
                url="/maintenance/scheduled",
                content=json.dumps(updated_content),
                headers={"Authorization": f"Bearer {login_and_get_token}"},
            )
            assert response.status_code == 200
            assert json.loads(response.content) is None
            assert json.load(tmp_file) == updated_content

            # Cache has been cleared so should get the new message back
            response = test_app.get(
                url="/maintenance/scheduled",
                headers={"Authorization": f"Bearer {login_and_get_token}"},
            )
            assert response.status_code == 200
            assert json.loads(response.content) == updated_content
