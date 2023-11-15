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
                "20230605100000",
                True,
                353,
                {"FE-204-LT-CAM-2-CENX": 5.83075538293604},
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
                "20230605100000",
                {
                    "FE-204-NSO-P1-CAM-1": "e155e7241af619e65e9d87b8b109c060",
                    "FE-204-NSO-P2-CAM-1": "576299fd37628f21d755c87a983e5b28",
                    "TS-202-TSM-CAM-2": "00a54a41f57d22353f6e21150059742f",
                },
                False,
                id="Ordinary request (preferred colour map not set)",
            ),
            pytest.param(
                "20230605100000",
                {
                    "FE-204-NSO-P1-CAM-1": "e99a52ef19d21df34dc07619d684a61a",
                    "FE-204-NSO-P2-CAM-1": "6b5dc42ec1110f1d229f3901deb07df1",
                    "TS-202-TSM-CAM-2": "af70df64de97b30fb7a7a54462825ade",
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
