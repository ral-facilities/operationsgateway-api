import json
from urllib.parse import quote

from fastapi.testclient import TestClient
import pytest


class TestGetCrosshairIntensity:
    @pytest.mark.parametrize(
        ["channel_name", "functions", "row", "column"],
        [
            pytest.param("FE-204-NSO-P1-CAM-1", None, [308, 337, 384], [240, 381, 235]),
            pytest.param(
                "a",
                {"name": "a", "expression": "FE-204-NSO-P1-CAM-1 / 10"},
                [30.8, 33.7, 38.4],
                [24.0, 38.1, 23.5],
            ),
        ],
    )
    def test_get_crosshair_intensity(
        self,
        channel_name: str,
        functions: dict[str, str],
        row: list[float],
        column: list[float],
        test_app: TestClient,
        login_and_get_token,
    ):
        url = f"/images/20230605100000/{channel_name}/crosshair"
        if functions is not None:
            url += f"?functions={quote(json.dumps(functions))}"
        test_response = test_app.get(
            url=url,
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_response.status_code == 200, test_response.content.decode()
        content_dict = json.loads(test_response.content.decode())

        assert content_dict["row"]["position"] == 607
        assert content_dict["row"]["fwhm"] == 621
        assert content_dict["row"]["intensity"]["x"][:3] == [0, 1, 2]
        assert content_dict["row"]["intensity"]["y"][:3] == row

        assert content_dict["column"]["position"] == 760
        assert content_dict["column"]["fwhm"] == 543
        assert content_dict["column"]["intensity"]["x"][:3] == [0, 1, 2]
        assert content_dict["column"]["intensity"]["y"][:3] == column
