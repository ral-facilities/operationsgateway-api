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
                    "N_COMP_FF_IMAGE": "2fa3239b5f46b110964f02a2e6c6dd62",
                    "N_COMP_NF_IMAGE": "16624db9b93bfe8176cd275d24522bc5",
                    "N_LEG1_GREEN_NF_IMAGE": "1fcf716b4f670dc4a901ca77ea0b8ee5",
                },
                False,
                id="Ordinary request (preferred colour map not set)",
            ),
            pytest.param(
                "20220408132830",
                {
                    "N_COMP_FF_IMAGE": "33e614585eb7e063174629cddedc5009",
                    "N_COMP_NF_IMAGE": "9431db428aab384aa83a06951cacb9be",
                    "N_LEG1_GREEN_NF_IMAGE": "c874477cf9018849cd4260615da129b6",
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
