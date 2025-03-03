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
        ", functions, expected_channels_data",
        [
            pytest.param(
                {"metadata.shotnum": {"$exists": True}},
                0,
                2,
                "metadata.shotnum ASC",
                None,
                False,
                [353, 377],
                [],
                [
                    {"TS-202-TSM-P1-CAM-2-CENX": 3.0393419803062542},
                    {"TS-202-TSM-P1-CAM-2-CENX": -3.0646222644792527},
                ],
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
                [],
                [
                    {
                        "_id": "20230605080000",
                        "metadata": {
                            "active_area": "las",
                            "epac_ops_data_version": "1.0",
                            "shotnum": 423648000000,
                            "timestamp": "2023-06-05T08:00:00",
                        },
                    },
                    {
                        "_id": "20230605090000",
                        "metadata": {
                            "active_area": "ea1",
                            "active_experiment": "22042898",
                            "epac_ops_data_version": "1.0",
                            "shotnum": 423648036000,
                            "timestamp": "2023-06-05T09:00:00",
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
                [],
                [
                    {
                        "_id": "20230605080000",
                        "metadata": {
                            "shotnum": 423648000000,
                            "timestamp": "2023-06-05T08:00:00",
                        },
                    },
                    {
                        "_id": "20230605090000",
                        "metadata": {
                            "shotnum": 423648036000,
                            "timestamp": "2023-06-05T09:00:00",
                        },
                    },
                ],
                id="Query using multiple projections",
            ),
            pytest.param(
                {"metadata.shotnum": {"$exists": True}},
                0,
                2,
                "metadata.shotnum ASC",
                ["channels.TS-202-TSM-P1-CAM-2-FWHMX.data"],
                False,
                None,
                [],
                [
                    {
                        "_id": "20230605080000",
                        "channels": {
                            "TS-202-TSM-P1-CAM-2-FWHMX": {"data": 46.402748185135856},
                        },
                    },
                    {
                        "_id": "20230605090000",
                        "channels": {
                            "TS-202-TSM-P1-CAM-2-FWHMX": {"data": 54.5600997950534},
                        },
                    },
                ],
                id="Query using a single channel projection",
            ),
            pytest.param(
                {"metadata.shotnum": 366351},
                0,
                2,
                "metadata.shotnum ASC",
                None,
                False,
                [353],
                [],
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
                [353, 377],
                [],
                [
                    {"TS-202-TSM-P1-CAM-2-CENX": 3.0393419803062542},
                    {"TS-202-TSM-P1-CAM-2-CENX": -3.0646222644792527},
                ],
                id="Query with truncate",
            ),
            pytest.param(
                {"metadata.shotnum": {"$exists": True}},
                0,
                2,
                "metadata.shotnum ASC",
                None,
                False,
                [354, 378],
                [{"name": "test", "expression": "1"}],
                [
                    {"TS-202-TSM-P1-CAM-2-CENX": 3.0393419803062542, "test": 1},
                    {"TS-202-TSM-P1-CAM-2-CENX": -3.0646222644792527, "test": 1},
                ],
                id="Example with functions",
            ),
            pytest.param(
                {"channels.CM-202-CVC-SP": {"$exists": True}},
                0,
                2,
                "metadata.shotnum ASC",
                None,
                False,
                [354, 378],
                [{"name": "test", "expression": "CM-202-CVC-SP - 700"}],
                [
                    {"test": "bab14eb3d04eb04e"},
                    {"test": "bab14eb0c14eb14f"},
                ],
                id="Example with Waveform function",
            ),
            pytest.param(
                {"channels.FE-204-NSO-P1-CAM-1": {"$exists": True}},
                0,
                2,
                "metadata.shotnum ASC",
                None,
                False,
                [354, 378],
                [{"name": "test", "expression": "FE-204-NSO-P1-CAM-1 - 700"}],
                [
                    {"test": "c73b39c0c00fcc7e"},
                    {"test": "c73c38e2c00fc73b"},
                ],
                id="Example with Image function",
            ),
            pytest.param(
                {"metadata.shotnum": 423648000000},
                0,
                1,
                "metadata.shotnum ASC",
                ["channels.CM-202-CVC-CAM-1.metadata"],
                False,
                None,
                [],
                [
                    {
                        "_id": "20230605080000",
                        "channels": {
                            "CM-202-CVC-CAM-1": {
                                "metadata": {
                                    "channel_dtype": "image",
                                    "exposure_time_s": 0.0012,
                                    "gain": 4.826012758558324,
                                },
                            },
                        },
                    },
                ],
                id="Query for bit_depth, not present",
            ),
            pytest.param(
                {"metadata.shotnum": 423649008000},
                0,
                1,
                "metadata.shotnum ASC",
                ["channels.CM-202-CVC-CAM-1.metadata"],
                False,
                None,
                [],
                [
                    {
                        "_id": "20230606120000",
                        "channels": {
                            "CM-202-CVC-CAM-1": {
                                "metadata": {
                                    "bit_depth": 12,
                                    "channel_dtype": "image",
                                    "exposure_time_s": 0.0012,
                                    "gain": 0.7862722445526737,
                                },
                            },
                        },
                    },
                ],
                id="Query for bit_depth, present",
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
        functions: "list[dict[str, str]]",
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

        functions_param = "".join([f"&functions={json.dumps(f)}" for f in functions])

        test_response = test_app.get(
            f"/records?{projection_param}&conditions={json.dumps(conditions)}"
            f"&skip={skip}&limit={limit}&order={order}&truncate={json.dumps(truncate)}"
            f"{functions_param}",
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
                {"metadata.shotnum": 423648072000},
                None,
                None,
                None,
                None,
                False,
                {
                    "TS-202-TSM-P2-CAM-1": "cdc134273f0e36e1",
                },
                id="Whole record: all channels have channel_dtype returned",
            ),
            # ensure setting the user's preferred colour map overrides the system
            # default
            pytest.param(
                {"metadata.shotnum": 423648072000},
                None,
                None,
                None,
                None,
                True,
                {
                    "TS-202-TSM-P2-CAM-1": "ccc139332d6c3733",
                },
                id="Whole record: all channels have channel_dtype returned and user's "
                "preferred colour map is set",
            ),
            pytest.param(
                {"metadata.shotnum": 423648072000},
                "channels.TS-202-TSM-P2-CAM-1.thumbnail",
                None,
                None,
                None,
                False,
                {
                    "TS-202-TSM-P2-CAM-1": "cdc134273f0e36e1",
                },
                id="Partial record: only TS-202-TSM-P2-CAM-1 and no channel_dtype"
                " returned",
            ),
            pytest.param(
                {"metadata.shotnum": 423648072000},
                None,
                50,
                200,
                "jet_r",
                False,
                {
                    "TS-202-TSM-P2-CAM-1": "8000000000000000",
                },
                id="Whole record: all channels have channel_dtype returned "
                "and custom false colour settings applied",
            ),
            # repeat the test above but with the user's preferred colour map set
            # ensure this does not affect the outcome
            pytest.param(
                {"metadata.shotnum": 423648072000},
                None,
                50,
                200,
                "jet_r",
                True,
                {
                    "TS-202-TSM-P2-CAM-1": "8000000000000000",
                },
                id="Whole record: all channels have channel_dtype returned "
                "and custom false colour settings applied even with user's "
                "preferred colour map set",
            ),
            pytest.param(
                {"metadata.shotnum": 423648072000},
                "channels.TS-202-TSM-P2-CAM-1.thumbnail",
                50,
                200,
                "jet_r",
                False,
                {
                    "TS-202-TSM-P2-CAM-1": "8000000000000000",
                },
                id="Partial record: only TS-202-TSM-P2-CAM-1 and no channel_dtype"
                " returned and custom false colour settings applied",
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
