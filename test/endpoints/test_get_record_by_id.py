import json

from fastapi.testclient import TestClient
import pytest

from test.conftest import assert_record, assert_thumbnails


class TestGetRecordByID:
    @pytest.mark.parametrize(
        "record_id, truncate, expected_channel_count, expected_channel_data",
        [
            pytest.param(
                "20220408094341",
                True,
                59,
                {"SAD_NF_E": -14.122},
                id="Ordinary request",
            ),
        ],
    )
    def test_valid_get_record_by_id(
        self,
        test_app: TestClient,
        login_and_get_token,
        record_id,
        truncate,
        expected_channel_count,
        expected_channel_data,
    ):
        test_response = test_app.get(
            f"/records/{record_id}?truncate={json.dumps(truncate)}",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_response.status_code == 200

        assert_record(
            test_response.json(),
            expected_channel_count,
            expected_channel_data,
        )

    @pytest.mark.parametrize(
        "record_id, expected_thumbnail_md5s",
        [
            pytest.param(
                "20220408132830",
                {
                    "N_COMP_FF_IMAGE": "c64d9a6021f52116ee722e824409dd66",
                    "N_COMP_NF_IMAGE": "a4e40908d17a2549a9785d0f320bd901",
                    "N_LEG1_GREEN_NF_IMAGE": "6cb214ab2d0b919bcb6bd61c59215d07",
                },
                id="Ordinary request",
            ),
        ],
    )
    def test_image_thumbnails_get_record_by_id(
        self,
        test_app: TestClient,
        login_and_get_token,
        record_id,
        expected_thumbnail_md5s,
    ):
        test_response = test_app.get(
            f"/records/{record_id}",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_response.status_code == 200

        assert_thumbnails(
            test_response.json(),
            expected_thumbnail_md5s,
        )
