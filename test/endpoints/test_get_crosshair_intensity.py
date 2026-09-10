import json
from urllib.parse import quote

from fastapi.testclient import TestClient
import pytest

from test.conftest import format_id


class TestGetCrosshairIntensity:
    @pytest.mark.parametrize(
        "apply_functions",
        [pytest.param(False), pytest.param(True)],
    )
    @pytest.mark.parametrize(
        (
            "record_id",
            "channel_name",
            "row_position",
            "row_fwhm",
            "row",
            "column_position",
            "column_fwhm",
            "column",
        ),
        [
            pytest.param(
                "20230605080000123",
                "FE-204-NSO-P1-CAM-1",
                609,
                616,
                [606, 582, 536],
                760,
                539,
                [543, 575, 339],
                id="16-bit image",
            ),
            pytest.param(
                "20230606120000456",
                "CM-202-CVC-CAM-1",
                612,
                607,
                [277, 28, 108],
                890,
                538,
                [480, 222, 376],
                id="12-bit image",
            ),
        ],
    )
    def test_get_crosshair_intensity(
        self,
        apply_functions: bool,
        record_id: str,
        channel_name: str,
        row_position: int,
        row_fwhm: int,
        row: list[float],
        column_position: int,
        column_fwhm: int,
        column: list[float],
        test_app: TestClient,
        login_and_get_token,
    ):
        record_id = format_id(record_id)

        if apply_functions:
            row = [value / 10 for value in row]
            column = [value / 10 for value in column]
            functions = json.dumps(
                {
                    "name": "a",
                    "expression": f"{channel_name} / 10",
                },
            )
            url = f"/images/{record_id}/a/crosshair" f"?functions={quote(functions)}"
        else:
            url = f"/images/{record_id}/{channel_name}/crosshair"

        test_response = test_app.get(
            url=url,
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_response.status_code == 200, test_response.content.decode()

        content_dict = test_response.json()

        assert content_dict["row"]["position"] == row_position
        assert content_dict["row"]["fwhm"] == row_fwhm
        assert content_dict["row"]["intensity"]["x"][:3] == [0, 1, 2]
        assert content_dict["row"]["intensity"]["y"][:3] == row

        assert content_dict["column"]["position"] == column_position
        assert content_dict["column"]["fwhm"] == column_fwhm
        assert content_dict["column"]["intensity"]["x"][:3] == [0, 1, 2]
        assert content_dict["column"]["intensity"]["y"][:3] == column
