import json

from fastapi.testclient import TestClient
import pytest

from test.conftest import assert_record


class TestGetRecordByID:
    @pytest.mark.parametrize(
        "record_id, truncate, expected_channel_count, expected_channel_data",
        [
            pytest.param(
                "62cd88520abfaa415fad6394",
                True,
                61,
                {"SAD_NF_E": -14.122},
                id="Ordinary request",
            ),
        ],
    )
    def test_valid_get_record_by_id(
        self,
        test_app: TestClient,
        record_id,
        truncate,
        expected_channel_count,
        expected_channel_data,
    ):
        # TODO - IDs must be standardised to ensure these tests pass across mutliple
        # machines. Completing DSEGOG-28 will resolve this

        test_response = test_app.get(
            f"/records/{record_id}?truncate={json.dumps(truncate)}",
        )

        assert test_response.status_code == 200

        assert_record(
            test_response.json(),
            expected_channel_count,
            expected_channel_data,
        )
