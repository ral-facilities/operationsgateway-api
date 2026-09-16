import json

from fastapi.testclient import TestClient
import pytest

from test.conftest import MARK_EPAC_TEST, MARK_GEMINI_TEST


class TestCountRecords:
    @pytest.mark.parametrize(
        "conditions, expected_count",
        [
            pytest.param(
                {},
                4,
                id="No conditions",
            ),
            pytest.param(
                {"metadata.shotnum": 423648000000},
                1,
                marks=MARK_EPAC_TEST,
                id="EPAC: Specific shot number",
            ),
            pytest.param(
                {"metadata.shotnum": {"$gt": 423648072000}},
                1,
                marks=MARK_EPAC_TEST,
                id="EPAC: Shot number range with operator",
            ),
            pytest.param(
                {
                    "metadata.shotnum": "20230605-075959",
                    "metadata.active_area": {"$in": ["GD"]},
                },
                1,
                marks=MARK_GEMINI_TEST,
                id="Gemini: Specific shot number",
            ),
            pytest.param(
                {
                    "metadata.shotnum": {"$gt": "20230605-120000"},
                    "metadata.active_area": {"$in": ["GD"]},
                },
                1,
                marks=MARK_GEMINI_TEST,
                id="Gemini: Shot number range with operator",
            ),
        ],
    )
    def test_valid_count_records(
        self,
        test_app: TestClient,
        login_and_get_token,
        conditions,
        expected_count,
    ):
        test_response = test_app.get(
            f"/records/count?conditions={json.dumps(conditions)}",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_response.status_code == 200
        assert test_response.json() == expected_count
