import json

from fastapi.testclient import TestClient
import pytest

from test.conftest import assert_record, assert_thumbnails


class TestGetRecords:
    @pytest.mark.parametrize(
        "conditions, skip, limit, order, projection, truncate, expected_channels_count"
        ", expected_channels_data",
        [
            pytest.param(
                {"metadata.shotnum": {"$exists": True}},
                0,
                2,
                "metadata.shotnum ASC",
                None,
                False,
                [59, 59],
                [{"N_COMP_FF_XPOS": 329.333}, {"N_COMP_FF_XPOS": 330.523}],
                id="Simple example",
            ),
            pytest.param(
                {"metadata.shotnum": 366351},
                0,
                2,
                "metadata.shotnum ASC",
                None,
                False,
                [59],
                [{"N_COMP_FF_XPOS": 323.75}],
                id="Query to retrieve specific shot",
            ),
            pytest.param(
                {"metadata.shotnum": {"$exists": True}},
                0,
                2,
                "metadata.shotnum ASC",
                None,
                True,
                [59, 59],
                [{"N_COMP_FF_XPOS": 329.333}, {"N_COMP_FF_XPOS": 330.523}],
                id="Query with truncate",
            ),
        ],
    )
    def test_valid_get_records(
        self,
        test_app: TestClient,
        login_and_get_token,
        conditions,
        skip,
        limit,
        order,
        projection,
        truncate,
        expected_channels_count,
        expected_channels_data,
    ):

        projection_param = (
            f"&projection={projection}" if isinstance(projection, list) else ""
        )

        test_response = test_app.get(
            f"/records?{projection_param}&conditions={json.dumps(conditions)}"
            f"&skip={skip}&limit={limit}&order={order}&truncate={json.dumps(truncate)}",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_response.status_code == 200

        for record, expected_channel_count, expected_channel_data in zip(  # noqa: B905
            test_response.json(),
            expected_channels_count,
            expected_channels_data,
        ):
            assert_record(record, expected_channel_count, expected_channel_data)

    @pytest.mark.parametrize(
        "conditions, projection, lower_level, upper_level, colourmap_name, "
        "expected_thumbnail_md5s",
        [
            pytest.param(
                {"metadata.shotnum": 366372},
                None,
                None,
                None,
                None,
                {
                    "N_COMP_NF_IMAGE": "9c938bb51dd810a00b619f425182b08d",
                },
                id="Whole record: all channels have channel_dtype returned",
            ),
            pytest.param(
                {"metadata.shotnum": 366372},
                "channels.N_COMP_NF_IMAGE.thumbnail",
                None,
                None,
                None,
                {
                    "N_COMP_NF_IMAGE": "9c938bb51dd810a00b619f425182b08d",
                },
                id="Partial record: only N_COMP_NF_IMAGE and no channel_dtype returned",
            ),
            pytest.param(
                {"metadata.shotnum": 366372},
                None,
                50,
                200,
                "jet_r",
                {
                    "N_COMP_NF_IMAGE": "128f9668b04185e9b5ba868854535992",
                },
                id="Whole record: all channels have channel_dtype returned "
                "and custom false colour settings applied",
            ),
            pytest.param(
                {"metadata.shotnum": 366372},
                "channels.N_COMP_NF_IMAGE.thumbnail",
                50,
                200,
                "jet_r",
                {
                    "N_COMP_NF_IMAGE": "128f9668b04185e9b5ba868854535992",
                },
                id="Partial record: only N_COMP_NF_IMAGE and no channel_dtype returned "
                "and custom false colour settings applied",
            ),
        ],
    )
    def test_image_thumbnails_get_records(
        self,
        test_app: TestClient,
        login_and_get_token,
        conditions,
        projection,
        lower_level,
        upper_level,
        colourmap_name,
        expected_thumbnail_md5s,
    ):

        query_string = ""
        query_params_array = []

        if conditions:
            query_params_array.append(f"conditions={json.dumps(conditions)}")
        if projection:
            query_params_array.append(f"projection={projection}")
        if lower_level:
            query_params_array.append(f"lower_level={lower_level}")
        if upper_level:
            query_params_array.append(f"upper_level={upper_level}")
        if colourmap_name:
            query_params_array.append(f"colourmap_name={colourmap_name}")

        if len(query_params_array) > 0:
            query_string = "?" + "&".join(query_params_array)

        test_response = test_app.get(
            f"/records{query_string}",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_response.status_code == 200

        assert_thumbnails(
            test_response.json()[0],  # only one record expected
            expected_thumbnail_md5s,
        )
