import json

from fastapi.testclient import TestClient
import pytest

from test.conftest import (
    assert_record,
    assert_thumbnails,
    set_preferred_colourmap,
    unset_preferred_colourmap,
)


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
        "record_id, expected_thumbnail_md5s, use_preferred_colourmap",
        [
            pytest.param(
                "20220408132830",
                {
                    "N_COMP_FF_IMAGE": "908dc69e252bd858286738558c5919a1",
                    "N_COMP_NF_IMAGE": "72b4d4f126181d47fcbfd03969a6fe80",
                    "N_LEG1_GREEN_NF_IMAGE": "6cb9867d9486a3d72a590119938a833e",
                },
                False,
                id="Ordinary request (preferred colour map not set)",
            ),
            pytest.param(
                "20220408132830",
                {
                    "N_COMP_FF_IMAGE": "99fd2686879c9939a45869c7399e8b2d",
                    "N_COMP_NF_IMAGE": "02a231b2d5452703d39e78d4084e9e04",
                    "N_LEG1_GREEN_NF_IMAGE": "24bb527a7e8b80770a88bfccc0a03180",
                },
                True,
                id="Ordinary request (with preferred colour map set)",
            ),
        ],
    )
    def test_image_thumbnails_get_record_by_id(
        self,
        test_app: TestClient,
        login_and_get_token,
        record_id,
        expected_thumbnail_md5s,
        use_preferred_colourmap,
    ):
        set_preferred_colourmap(test_app, login_and_get_token, use_preferred_colourmap)

        test_response = test_app.get(
            f"/records/{record_id}",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        unset_preferred_colourmap(
            test_app,
            login_and_get_token,
            use_preferred_colourmap,
        )

        assert test_response.status_code == 200

        assert_thumbnails(
            test_response.json(),
            expected_thumbnail_md5s,
        )
