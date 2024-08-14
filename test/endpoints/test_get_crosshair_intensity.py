import json

from fastapi.testclient import TestClient


class TestGetCrosshairIntensity:
    def test_get_crosshair_intensity(
        self,
        test_app: TestClient,
        login_and_get_token,
    ):
        test_response = test_app.get(
            "/images/20230605100000/FE-204-NSO-P1-CAM-1/crosshair",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_response.status_code == 200, test_response.content.decode()
        content_dict = json.loads(test_response.content.decode())

        assert content_dict["row"]["position"] == 607
        assert content_dict["row"]["fwhm"] == 621
        assert content_dict["row"]["intensity"]["x"][:3] == [0, 1, 2]
        assert content_dict["row"]["intensity"]["y"][:3] == [308, 337, 384]

        assert content_dict["column"]["position"] == 760
        assert content_dict["column"]["fwhm"] == 543
        assert content_dict["column"]["intensity"]["x"][:3] == [0, 1, 2]
        assert content_dict["column"]["intensity"]["y"][:3] == [240, 381, 235]
