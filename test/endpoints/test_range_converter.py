import json

from fastapi.testclient import TestClient
import pytest

from operationsgateway_api.src.exceptions import ModelError
from operationsgateway_api.src.models import ShotnumConverterRange
from test.conftest import MARK_EPAC_TEST, MARK_GEMINI_TEST


class TestRangeConverter:
    @pytest.mark.parametrize(
        "date_range, shotnum_range, expected_response",
        [
            pytest.param(
                None,
                {"min": 423648001800, "max": 423648291600},
                {"from": "2023-06-05T08:03:00", "to": "2023-06-05T08:03:00"},
                marks=MARK_EPAC_TEST,
                id="EPAC: Shotnum to date range",
            ),
            pytest.param(
                {"from": "2023-06-05 08:02:19", "to": "2023-06-05 21:00:00"},
                None,
                {"min": 423648001800, "max": 423648001800},
                marks=MARK_EPAC_TEST,
                id="EPAC: Date to shotnum range",
            ),
            pytest.param(
                None,
                {"min": 1234, "max": 423648072000},
                {"from": "2023-06-05T08:00:00", "to": "2023-06-05T08:03:00"},
                marks=MARK_EPAC_TEST,
                id=(
                    "EPAC: Shotnum to date range where min shotnum < first shotnum "
                    "stored in database"
                ),
            ),
            pytest.param(
                None,
                {"min": 423648072000, "max": 999999999999},
                {"from": "2023-06-06T12:00:00", "to": "2023-06-06T12:00:00"},
                marks=MARK_EPAC_TEST,
                id=(
                    "EPAC: Shotnum to date range where max shotnum > last shotnum "
                    "stored in database"
                ),
            ),
            pytest.param(
                {"from": "2000-01-01 00:00:00", "to": "2023-06-05 12:00:00"},
                None,
                {"min": 423648000000, "max": 423648001800},
                marks=MARK_EPAC_TEST,
                id=(
                    "EPAC: Date to shotnum range where from date < first timestamp "
                    "stored in database"
                ),
            ),
            pytest.param(
                {"from": "2022-04-07T15:10:00", "to": "2100-01-01 18:00:00"},
                None,
                {"min": 423648000000, "max": 423649008000},
                marks=MARK_EPAC_TEST,
                id=(
                    "EPAC: Date to shotnum range where to date > last timestamp stored "
                    "in database"
                ),
            ),
            pytest.param(
                None,
                {"min": "20230605-080000", "max": "20230605-090000", "type": "GD"},
                {
                    "from": "2023-06-05T08:03:00.234000",
                    "to": "2023-06-05T08:03:00.234000",
                },
                marks=MARK_GEMINI_TEST,
                id="Gemini: Shotnum to date range",
            ),
            pytest.param(
                {
                    "from": "2023-06-05 08:02:19",
                    "to": "2023-06-05 21:00:00",
                    "type": "GD",
                },
                None,
                {"min": "20230605-080259", "max": "20230605-080259"},
                marks=MARK_GEMINI_TEST,
                id="Gemini: Date to shotnum range",
            ),
            pytest.param(
                None,
                {"min": "20200101-080000", "max": "20230605-090000", "type": "GD"},
                {
                    "from": "2023-06-05T08:00:00.123000",
                    "to": "2023-06-05T08:03:00.234000",
                },
                marks=MARK_GEMINI_TEST,
                id=(
                    "Gemini: Shotnum to date range where min shotnum < first shotnum "
                    "stored in database"
                ),
            ),
            pytest.param(
                None,
                {"min": "20230605-080000", "max": "30000101-090000", "type": "GD"},
                {
                    "from": "2023-06-05T08:03:00.234000",
                    "to": "2023-06-06T12:00:00.456000",
                },
                marks=MARK_GEMINI_TEST,
                id=(
                    "Gemini: Shotnum to date range where max shotnum > last shotnum "
                    "stored in database"
                ),
            ),
            pytest.param(
                {
                    "from": "2000-01-01 00:00:00",
                    "to": "2023-06-05 12:00:00",
                    "type": "GD",
                },
                None,
                {"min": "20230605-075959", "max": "20230605-080259"},
                marks=MARK_GEMINI_TEST,
                id=(
                    "Gemini: Date to shotnum range where from date < first timestamp "
                    "stored in database"
                ),
            ),
            pytest.param(
                {
                    "from": "2022-04-07T15:10:00",
                    "to": "2100-01-01 18:00:00",
                    "type": "GD",
                },
                None,
                {"min": "20230605-075959", "max": "20230606-115959"},
                marks=MARK_GEMINI_TEST,
                id=(
                    "Gemini: Date to shotnum range where to date > last timestamp "
                    "stored in database"
                ),
            ),
        ],
    )
    def test_valid_range_converter(
        self,
        test_app: TestClient,
        login_and_get_token,
        date_range,
        shotnum_range,
        expected_response,
    ):
        if shotnum_range:
            input_range_query_params = f"shotnum_range={json.dumps(shotnum_range)}"
        elif date_range:
            input_range_query_params = f"date_range={json.dumps(date_range)}"

        test_response = test_app.get(
            f"/records/range_converter?{input_range_query_params}",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_response.status_code == 200

        assert test_response.json() == expected_response

    @pytest.mark.parametrize(
        "date_range, shotnum_range, expected_status_code",
        [
            pytest.param(
                None,
                {"min": 1234, "max": 2345},
                500,
                id="Min and max shotnum outside range of stored shot numbers",
            ),
            pytest.param(
                {"from": "2000-01-01 00:00:00", "to": "2000-02-02 00:00:00"},
                None,
                500,
                id="From and to date outside range of stored timestamps",
            ),
            pytest.param(
                None,
                {"min": 366280, "max": 366275},
                400,
                id="Max shotnum > min shotnum",
            ),
            pytest.param(
                {"from": "2022-04-07T14:00:00", "to": "2022-04-07T12:00:00"},
                None,
                400,
                id="To date > from date",
            ),
            pytest.param(
                {"from": "Not a date", "to": "Also not a date"},
                None,
                400,
                id="Strings sent instead of dates",
            ),
            pytest.param(
                None,
                {"min": "Not a shotnum", "max": "Also not a shotnum"},
                400,
                id="Strings sent instead of shotnums",
            ),
            pytest.param(
                {"from": "2022-04-07 14:16:19", "to": "2022-04-07 21:00:00"},
                {"min": 366275, "max": 366280},
                400,
                id="Date range and shotnum range provided in query parameters",
            ),
        ],
    )
    def test_invalid_range_converter(
        self,
        test_app: TestClient,
        login_and_get_token,
        date_range,
        shotnum_range,
        expected_status_code,
    ):
        if shotnum_range and date_range:
            input_range_query_params = (
                f"shotnum_range={json.dumps(shotnum_range)}"
                f"&date_range={json.dumps(date_range)}"
            )
        elif shotnum_range:
            input_range_query_params = f"shotnum_range={json.dumps(shotnum_range)}"
        elif date_range:
            input_range_query_params = f"date_range={json.dumps(date_range)}"

        test_response = test_app.get(
            f"/records/range_converter?{input_range_query_params}",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_response.status_code == expected_status_code


class TestShotnumConverterRange:
    """
    Unit tests for the ShotnumConverterRange model.

    These tests validate the handling of both integer and typed string shot numbers:
    - Integers are accepted when no type is provided
    - Strings are accepted when a valid type (GA, GS, GQ, GD) is provided
    - Mixing integers and strings is rejected
    - Shot number prefixes must match the specified type
    - Range ordering (min <= max) is enforced
    - Invalid formats (including GD formatting) are rejected

    These are model-level tests and do not rely on database state as we
    don't have any data yet.
    """

    @pytest.mark.parametrize(
        "payload",
        [
            pytest.param(
                {"min": 123, "max": 456},
                id="Int shotnums without type",
            ),
            pytest.param(
                {"type": "GA", "min": "GA123", "max": "GA456"},
                id="GA shotnums with type",
            ),
            pytest.param(
                {"type": "GS", "min": "GS001", "max": "GS999"},
                id="GS shotnums with type",
            ),
            pytest.param(
                {"type": "GQ", "min": "GQ100", "max": "GQ200"},
                id="GQ shotnums with type",
            ),
            pytest.param(
                {"type": "GD", "min": "20240101-120000", "max": "20240101-130000"},
                id="GD shotnums with type",
            ),
        ],
    )
    def test_valid_shotnum_converter_range(self, payload):
        model = ShotnumConverterRange(**payload)

        assert model is not None

    @pytest.mark.parametrize(
        "payload",
        [
            pytest.param(
                {"min": "GA123", "max": "GA456"},
                id="String shotnums without type",
            ),
            pytest.param(
                {"type": "GA", "min": 123, "max": 456},
                id="Int shotnums with type",
            ),
            pytest.param(
                {"type": "GA", "min": "GA123", "max": 456},
                id="Mixed min string max int",
            ),
            pytest.param(
                {"type": "GA", "min": 123, "max": "GA456"},
                id="Mixed min int max string",
            ),
            pytest.param(
                {"type": "GS", "min": "GA123", "max": "GS456"},
                id="Min shotnum does not match type",
            ),
            pytest.param(
                {"type": "GS", "min": "GS123", "max": "GA456"},
                id="Max shotnum does not match type",
            ),
            pytest.param(
                {"type": "GA", "min": "GA456", "max": "GA123"},
                id="Max less than min for typed shotnums",
            ),
            pytest.param(
                {"min": 456, "max": 123},
                id="Max less than min for int shotnums",
            ),
            pytest.param(
                {"type": "GD", "min": "GD20240101", "max": "GD20240102"},
                id="GD wrong format length",
            ),
        ],
    )
    def test_invalid_shotnum_converter_range(self, payload):
        with pytest.raises(ModelError):
            ShotnumConverterRange(**payload)
