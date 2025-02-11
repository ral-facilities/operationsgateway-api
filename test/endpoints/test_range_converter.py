import json

from fastapi.testclient import TestClient
import pytest


class TestRangeConverter:
    @pytest.mark.parametrize(
        "date_range, shotnum_range, expected_response",
        [
            pytest.param(
                None,
                {"min": 423648036000, "max": 423648288000},
                {"from": "2023-06-05T09:00:00", "to": "2023-06-05T16:00:00"},
                id="Shotnum to date range",
            ),
            pytest.param(
                {"from": "2023-06-05 08:16:19", "to": "2023-06-05 21:00:00"},
                None,
                {"min": 423648036000, "max": 423648288000},
                id="Date to shotnum range",
            ),
            pytest.param(
                None,
                {"min": 1234, "max": 423648072000},
                {"from": "2023-06-05T08:00:00", "to": "2023-06-05T10:00:00"},
                id="Shotnum to date range where min shotnum < first shotnum stored in"
                " database",
            ),
            pytest.param(
                None,
                {"min": 423648072000, "max": 999999999999},
                {"from": "2023-06-05T10:00:00", "to": "2023-06-06T12:00:00"},
                id="Shotnum to date range where max shotnum > last shotnum stored in"
                " database",
            ),
            pytest.param(
                {"from": "2000-01-01 00:00:00", "to": "2023-06-05 12:00:00"},
                None,
                {"min": 423648000000, "max": 423648144000},
                id="Date to shotnum range where from date < first timestamp stored in"
                " database",
            ),
            pytest.param(
                {"from": "2022-04-07T15:10:00", "to": "2100-01-01 18:00:00"},
                None,
                {"min": 423648000000, "max": 423649008000},
                id="Date to shotnum range where to date > last timestamp stored in"
                " database",
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
