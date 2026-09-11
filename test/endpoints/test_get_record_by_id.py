import json

from fastapi.testclient import TestClient
import pytest

from test.conftest import (
    assert_record,
    assert_thumbnails,
    MARK_EPAC_TEST,
    MARK_GEMINI_TEST,
    RECORD_ID_05_0800,
    set_preferred_colourmap,
    unset_preferred_colourmap,
)


class TestGetRecordByID:
    @pytest.mark.parametrize(
        "record_id, truncate, expected_channel_count, expected_channel_data",
        [
            pytest.param(
                "20230605080000",
                True,
                353,
                {"FE-204-LT-CAM-2-CENX": 3.2117051242303507},
                marks=MARK_EPAC_TEST,
                id="EPAC: Ordinary request",
            ),
            pytest.param(
                "20230605080000123",
                True,
                354,  # Additional string channel
                {"FE-204-LT-CAM-2-CENX": 3.2117051242303507},
                marks=MARK_GEMINI_TEST,
                id="Gemini: Ordinary request",
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
        ["expected_thumbnails_hashes", "use_preferred_colourmap"],
        [
            pytest.param(
                {
                    "FE-204-NSO-P1-CAM-1": "c03e3df03fd90319",
                    "FE-204-NSO-P2-CAM-1": "cccc33273d623e85",
                    "TS-202-TSM-CAM-2": "cc3333cccc3333cc",
                },
                False,
                id="Ordinary request (preferred colour map not set)",
            ),
            pytest.param(
                {
                    "FE-204-NSO-P1-CAM-1": "c33f39c338c33839",
                    "FE-204-NSO-P2-CAM-1": "ccca33b621963f85",
                    "TS-202-TSM-CAM-2": "cc3333cccc3333cc",
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
        expected_thumbnails_hashes,
        use_preferred_colourmap,
    ):
        set_preferred_colourmap(test_app, login_and_get_token, use_preferred_colourmap)

        test_response = test_app.get(
            f"/records/{RECORD_ID_05_0800}",
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
