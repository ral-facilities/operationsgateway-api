import json

from fastapi.testclient import TestClient
import pytest

from test.conftest import assert_record


class TestGetRecords:
    @pytest.mark.parametrize(
        "conditions, skip, limit, order, projection, truncate, expected_channels_count"
        ", expected_channels_data",
        [
            pytest.param(
                {"metadata.shotnum": {"$exists": True}},
                0,
                2,
                "metadata.shotnum ASC",
                None,
                False,
                [59, 59],
                [{"N_COMP_FF_XPOS": 329.333}, {"N_COMP_FF_XPOS": 330.523}],
                id="Simple example",
            ),
            pytest.param(
                {"metadata.shotnum": 366351},
                0,
                2,
                "metadata.shotnum ASC",
                None,
                False,
                [59],
                [{"N_COMP_FF_XPOS": 323.75}],
                id="Query to retrieve specific shot",
            ),
            pytest.param(
                {"metadata.shotnum": {"$exists": True}},
                0,
                2,
                "metadata.shotnum ASC",
                None,
                True,
                [59, 59],
                [{"N_COMP_FF_XPOS": 329.333}, {"N_COMP_FF_XPOS": 330.523}],
                id="Query with truncate",
            ),
        ],
    )
    def test_valid_get_records(
        self,
        test_app: TestClient,
        login_and_get_token,
        conditions,
        skip,
        limit,
        order,
        projection,
        truncate,
        expected_channels_count,
        expected_channels_data,
    ):

        projection_param = (
            f"&projection={projection}" if isinstance(projection, list) else ""
        )

        test_response = test_app.get(
            f"/records?{projection_param}&conditions={json.dumps(conditions)}"
            f"&skip={skip}&limit={limit}&order={order}&truncate={json.dumps(truncate)}",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_response.status_code == 200

        for record, expected_channel_count, expected_channel_data in zip(
            test_response.json(),
            expected_channels_count,
            expected_channels_data,
        ):
            assert_record(record, expected_channel_count, expected_channel_data)
