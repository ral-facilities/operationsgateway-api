from fastapi.testclient import TestClient
import pytest

from operationsgateway_api.src.records.false_colour_handler import FalseColourHandler


class TestGetColourMapNames:
    @pytest.mark.parametrize(
        "",
        [
            pytest.param(
                id="Get all colourmap names",
            ),
        ],
    )
    def test_get_colourmap_names(
        self,
        test_app: TestClient,
        login_and_get_token,
    ):
        test_response = test_app.get(
            "/images/colourmap_names",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_response.status_code == 200

        assert test_response.json() == FalseColourHandler.colourmap_names
