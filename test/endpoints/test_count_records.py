import json

from fastapi.testclient import TestClient
import pytest


class TestCountRecords:
    @pytest.mark.parametrize(
        "conditions, expected_count",
        [
            pytest.param(
                {},
                399,
                id="No conditions",
            ),
            pytest.param(
                {"metadata.shotnum": 423648000000},
                1,
                id="Specific shot number",
            ),
            pytest.param(
                {"metadata.shotnum": {"$gt": 423648072000}},
                6,
                id="Shot number range with operator",
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
