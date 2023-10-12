import json

from fastapi.testclient import TestClient
import pytest


class TestRangeConverter:
    @pytest.mark.parametrize(
        "date_range, shotnum_range, expected_response",
        [
            pytest.param(
                None,
                {"min": 366275, "max": 366280},
                {"from": "2022-04-07T15:05:38", "to": "2022-04-08T00:21:14"},
                id="Shotnum to date range",
            ),
            pytest.param(
                {"from": "2022-04-07 14:16:19", "to": "2022-04-07 21:00:00"},
                None,
                {"min": 366272, "max": 366278},
                id="Date to shotnum range",
            ),
            pytest.param(
                None,
                {"min": 1234, "max": 366280},
                {"from": "2022-04-07T14:16:16", "to": "2022-04-08T00:21:14"},
                id="Shotnum to date range where min shotnum < first shotnum stored in"
                " database",
            ),
            pytest.param(
                None,
                {"min": 366350, "max": 9999999},
                {"from": "2022-04-08T09:43:41", "to": "2022-04-08T16:58:57"},
                id="Shotnum to date range where max shotnum > last shotnum stored in"
                " database",
            ),
            pytest.param(
                {"from": "2000-01-01 00:00:00", "to": "2022-04-08 15:00:00"},
                None,
                {"min": 366271, "max": 366367},
                id="Date to shotnum range where from date < first timestamp stored in"
                " database",
            ),
            pytest.param(
                {"from": "2022-04-07T15:10:00", "to": "2100-01-01 18:00:00"},
                None,
                {"min": 366276, "max": 366376},
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
