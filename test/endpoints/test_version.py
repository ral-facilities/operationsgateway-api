from fastapi.testclient import TestClient


class TestVersion:
    """
    Test to check that the /version endpoint returns a 200 response and includes
    the expected version string in the response JSON.
    """

    def test_version(self, test_app: TestClient):
        response = test_app.get("/version")
        assert response.status_code == 200
        assert "version" in response.json()
        assert isinstance(response.json()["version"], str)
