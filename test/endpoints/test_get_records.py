import json

from fastapi.testclient import TestClient
import pytest

from test.conftest import (
    assert_record,
    assert_thumbnails,
    set_preferred_colourmap,
    unset_preferred_colourmap,
)


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
                {"metadata.shotnum": {"$exists": True}},
                0,
                2,
                "metadata.shotnum ASC",
                ["metadata"],
                False,
                None,
                [
                    {
                        "_id": "20220407141616",
                        "metadata": {
                            "epac_ops_data_version": "1.0",
                            "shotnum": 366271,
                            "timestamp": "2022-04-07T14:16:16",
                        },
                    },
                    {
                        "_id": "20220407142816",
                        "metadata": {
                            "epac_ops_data_version": "1.0",
                            "shotnum": 366272,
                            "timestamp": "2022-04-07T14:28:16",
                        },
                    },
                ],
                id="Query using a single projection",
            ),
            pytest.param(
                {"metadata.shotnum": {"$exists": True}},
                0,
                2,
                "metadata.shotnum ASC",
                ["metadata.shotnum", "metadata.timestamp"],
                False,
                None,
                [
                    {
                        "_id": "20220407141616",
                        "metadata": {
                            "shotnum": 366271,
                            "timestamp": "2022-04-07T14:16:16",
                        },
                    },
                    {
                        "_id": "20220407142816",
                        "metadata": {
                            "shotnum": 366272,
                            "timestamp": "2022-04-07T14:28:16",
                        },
                    },
                ],
                id="Query using a multiple projections",
            ),
            pytest.param(
                {"metadata.shotnum": {"$exists": True}},
                0,
                2,
                "metadata.shotnum ASC",
                ["channels.N_COMP_FF_YPOS.data"],
                False,
                None,
                [
                    {
                        "_id": "20220407141616",
                        "channels": {
                            "N_COMP_FF_YPOS": {"data": 235.734},
                        },
                    },
                    {
                        "_id": "20220407142816",
                        "channels": {
                            "N_COMP_FF_YPOS": {"data": 243.771},
                        },
                    },
                ],
                id="Query using a single channels projection",
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
        if isinstance(projection, list):
            projection_param = "".join(
                [f"&projection={field_name}" for field_name in projection],
            )
        else:
            projection_param = ""

        print(f"Projection Param: {projection_param}")

        test_response = test_app.get(
            f"/records?{projection_param}&conditions={json.dumps(conditions)}"
            f"&skip={skip}&limit={limit}&order={order}&truncate={json.dumps(truncate)}",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_response.status_code == 200

        if not expected_channels_count:
            # Testing a request with no channels, most likely a query containing
            # projection so we cannot assume assert_record() will work
            assert test_response.json() == expected_channels_data
        else:
            for (
                record,
                expected_channel_count,
                expected_channel_data,
            ) in zip(  # noqa: B905
                test_response.json(),
                expected_channels_count,
                expected_channels_data,
            ):
                assert_record(record, expected_channel_count, expected_channel_data)

    @pytest.mark.parametrize(
        "conditions, projection, lower_level, upper_level, colourmap_name, "
        "use_preferred_colourmap, expected_thumbnails_hashes",
        [
            pytest.param(
                {"metadata.shotnum": 366372},
                None,
                None,
                None,
                None,
                False,
                {
                    "N_COMP_NF_IMAGE": "c0c73f8f783c3930",
                },
                id="Whole record: all channels have channel_dtype returned",
            ),
            # ensure setting the user's preferred colour map overrides the system
            # default
            pytest.param(
                {"metadata.shotnum": 366372},
                None,
                None,
                None,
                None,
                True,
                {
                    "N_COMP_NF_IMAGE": "c2c73f0f783c3330",
                },
                id="Whole record: all channels have channel_dtype returned and user's "
                "preferred colour map is set",
            ),
            pytest.param(
                {"metadata.shotnum": 366372},
                "channels.N_COMP_NF_IMAGE.thumbnail",
                None,
                None,
                None,
                False,
                {
                    "N_COMP_NF_IMAGE": "c0c73f8f783c3930",
                },
                id="Partial record: only N_COMP_NF_IMAGE and no channel_dtype returned",
            ),
            pytest.param(
                {"metadata.shotnum": 366372},
                None,
                50,
                200,
                "jet_r",
                False,
                {
                    "N_COMP_NF_IMAGE": "c3c13f0fc0383f8d",
                },
                id="Whole record: all channels have channel_dtype returned "
                "and custom false colour settings applied",
            ),
            # repeat the test above but with the user's preferred colour map set
            # ensure this does not affect the outcome
            pytest.param(
                {"metadata.shotnum": 366372},
                None,
                50,
                200,
                "jet_r",
                True,
                {
                    "N_COMP_NF_IMAGE": "c3c13f0fc0383f8d",
                },
                id="Whole record: all channels have channel_dtype returned "
                "and custom false colour settings applied even with user's "
                "preferred colour map set",
            ),
            pytest.param(
                {"metadata.shotnum": 366372},
                "channels.N_COMP_NF_IMAGE.thumbnail",
                50,
                200,
                "jet_r",
                False,
                {
                    "N_COMP_NF_IMAGE": "c3c13f0fc0383f8d",
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
        use_preferred_colourmap,
        expected_thumbnails_hashes,
    ):
        set_preferred_colourmap(test_app, login_and_get_token, use_preferred_colourmap)

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

        unset_preferred_colourmap(
            test_app,
            login_and_get_token,
            use_preferred_colourmap,
        )

        assert test_response.status_code == 200

        assert_thumbnails(
            test_response.json()[0],  # only one record expected
            expected_thumbnails_hashes,
        )
