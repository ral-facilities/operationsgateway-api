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
                    "N_COMP_FF_IMAGE": "b64a902e52a222d3b2c20c3eaf40fd5b",
                    "N_COMP_NF_IMAGE": "cfd90fafa84a5b24eb66081d26bf4e6a",
                    "N_LEG1_GREEN_NF_IMAGE": "565bd02fae8bf282a62546031cafd081",
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
