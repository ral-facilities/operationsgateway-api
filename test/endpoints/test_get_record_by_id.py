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
        "record_id, expected_thumbnails_hashes, use_preferred_colourmap",
        [
            pytest.param(
                "20230605100000",
                {
                    "FE-204-NSO-P1-CAM-1": "c4bc3f33381c98c7",
                    "FE-204-NSO-P2-CAM-1": "cd3336f0329b311d",
                    "TS-202-TSM-CAM-2": "9999666699996666",
                },
                False,
                id="Ordinary request (preferred colour map not set)",
            ),
            pytest.param(
                "20230605100000",
                {
                    "FE-204-NSO-P1-CAM-1": "c4b83f233b1839c7",
                    "FE-204-NSO-P2-CAM-1": "cd3336b234333639",
                    "TS-202-TSM-CAM-2": "9999666699996666",
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
        expected_thumbnails_hashes,
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
            expected_thumbnails_hashes,
        )
