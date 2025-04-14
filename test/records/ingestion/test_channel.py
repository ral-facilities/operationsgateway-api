import numpy as np
from pydantic import BaseModel
import pytest

from operationsgateway_api.src.channels.channel_manifest import ChannelManifest
from operationsgateway_api.src.models import ScalarChannelMetadataModel
from operationsgateway_api.src.records.ingestion.channel_checks import ChannelChecks
from test.records.ingestion.create_test_hdf import create_test_hdf_file


def create_channel_response(responses, extra=None, channels=False):
    """
    uses expected rejected channels from the test functions to generate a channel
    response to assert that the real channel response is what was expected
    (used so the expected response code doesn't need to be duplicated)
    """
    model_response = {
        "accepted_channels": [
            "CM-202-CVC-WFS",
            "CM-202-CVC-WFS-COEF",
            "PM-201-FE-CAM-1",
            "PM-201-FE-CAM-2",
            "PM-201-FE-CAM-2-CENX",
            "PM-201-FE-CAM-2-CENY",
            "PM-201-FE-CAM-2-FWHMX",
            "PM-201-FE-CAM-2-FWHMY",
            "PM-201-FE-EM",
            "PM-201-HJ-PD",
            "PM-201-PA1-EM",
            "PM-201-PA2-EM",
            "PM-201-TJ-CAM-2-CENX",
            "PM-201-TJ-CAM-2-CENY",
            "PM-201-TJ-CAM-2-FWHMX",
            "PM-201-TJ-CAM-2-FWHMY",
            "PM-201-TJ-EM",
        ],
        "rejected_channels": {},
    }

    if extra:
        responses = extra

    if channels:
        model_response["accepted_channels"].remove("PM-201-TJ-CAM-2-CENX")

    for response in responses:
        for channel, message in response.items():
            if channel in model_response["accepted_channels"]:
                model_response["accepted_channels"].remove(channel)

            if channel not in model_response["rejected_channels"]:
                model_response["rejected_channels"][channel] = [message]
            else:
                if message not in model_response["rejected_channels"][channel]:
                    (model_response["rejected_channels"][channel]).extend([message])

    return model_response


class TestChannel:
    @pytest.mark.asyncio
    async def test_channel_checks_success(self, remove_hdf_file):
        hdf_tuple = await create_test_hdf_file()
        channel_checker = ChannelChecks(*hdf_tuple)
        manifest = await ChannelManifest.get_most_recent_manifest()
        channel_checker.set_channels(manifest)
        async_functions = [
            channel_checker.channel_dtype_checks,
            channel_checker.channel_name_check,
        ]
        functions = [
            channel_checker.required_attribute_checks,
            channel_checker.optional_dtype_checks,
            channel_checker.dataset_checks,
            channel_checker.unrecognised_attribute_checks,
        ]

        for function in functions:
            assert function() == []

        for async_function in async_functions:
            assert await async_function() == []

        assert await channel_checker.channel_checks() == {
            "accepted_channels": [
                "CM-202-CVC-WFS",
                "CM-202-CVC-WFS-COEF",
                "PM-201-FE-CAM-1",
                "PM-201-FE-CAM-2",
                "PM-201-FE-CAM-2-CENX",
                "PM-201-FE-CAM-2-CENY",
                "PM-201-FE-CAM-2-FWHMX",
                "PM-201-FE-CAM-2-FWHMY",
                "PM-201-FE-EM",
                "PM-201-HJ-PD",
                "PM-201-PA1-EM",
                "PM-201-PA2-EM",
                "PM-201-TJ-CAM-2-CENX",
                "PM-201-TJ-CAM-2-CENY",
                "PM-201-TJ-CAM-2-FWHMX",
                "PM-201-TJ-CAM-2-FWHMY",
                "PM-201-TJ-EM",
            ],
            "rejected_channels": {},
        }

    @pytest.mark.parametrize(
        "altered_channel, response",
        [
            pytest.param(
                ["scalar", "missing", "scalar"],
                [
                    {"PM-201-FE-CAM-2-CENX": "channel_dtype attribute is missing"},
                ],
                id="Scalar channel_dtype missing",
            ),
            pytest.param(
                ["image", "missing", "image"],
                [
                    {"PM-201-FE-CAM-1": "channel_dtype attribute is missing"},
                ],
                id="Image channel_dtype missing",
            ),
            pytest.param(
                ["waveform", "missing", "waveform"],
                [
                    {"PM-201-HJ-PD": "channel_dtype attribute is missing"},
                ],
                id="Waveform channel_dtype missing",
            ),
            pytest.param(
                [487, "exists", "scalar"],
                [
                    {
                        "PM-201-FE-CAM-2-CENX": "channel_dtype has wrong data "
                        "type or its value is unsupported",
                    },
                ],
                id="Scalar channel_dtype incorrect",
            ),
            pytest.param(
                ["487", "exists", "image"],
                [
                    {
                        "PM-201-FE-CAM-1": "channel_dtype has wrong data type "
                        "or its value is unsupported",
                    },
                ],
                id="Image channel_dtype incorrect",
            ),
            pytest.param(
                ["None", "exists", "waveform"],
                [
                    {
                        "PM-201-HJ-PD": "channel_dtype has wrong data "
                        "type or its value is unsupported",
                    },
                ],
                id="Waveform channel_dtype incorrect",
            ),
            pytest.param(
                [
                    ["wrong", "exists"],
                    ["image", "exists"],
                    ["image", "missing"],
                    [487, "exists"],
                ],
                [
                    {"PM-201-FE-CAM-1": "channel_dtype attribute is missing"},
                    {
                        "PM-201-FE-CAM-2-CENX": "channel_dtype has wrong data "
                        "type or its value is unsupported",
                    },
                    {
                        "PM-201-FE-CAM-2-FWHMX": "channel_dtype has wrong data "
                        "type or its value is unsupported",
                    },
                    {
                        "PM-201-HJ-PD": "channel_dtype has wrong data type "
                        "or its value is unsupported",
                    },
                ],
                id="Multiple channel_dtype fails",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_channel_dtype_fail(self, remove_hdf_file, altered_channel, response):
        hdf_tuple = await create_test_hdf_file(channel_dtype=altered_channel)
        channel_checker = ChannelChecks(*hdf_tuple)
        manifest = await ChannelManifest.get_most_recent_manifest()
        channel_checker.set_channels(manifest)

        channel_response = create_channel_response(response)
        assert await channel_checker.channel_checks() == channel_response
        assert await channel_checker.channel_dtype_checks() == response

    @pytest.mark.parametrize(
        "required_attributes, response, extra",
        [
            pytest.param(
                {"scalar": {"data": "missing"}},
                [
                    {
                        "PM-201-FE-EM": "data attribute is missing",
                    },
                ],
                None,
                id="Scalar data missing",
            ),
            pytest.param(
                {"scalar": {"data": ["list type"]}},
                [
                    {
                        "PM-201-FE-EM": "data has wrong datatype",
                    },
                ],
                None,
                id="Scalar data invalid",
            ),
            pytest.param(
                {"image": {"data": "missing"}},
                [
                    {
                        "PM-201-FE-CAM-1": "data attribute is missing",
                    },
                ],
                None,
                id="Image data missing",
            ),
            pytest.param(
                {"image": {"data": 42}},
                [
                    {
                        "PM-201-FE-CAM-1": "data attribute has wrong datatype, "
                        "should be ndarray",
                    },
                ],
                [
                    {
                        "PM-201-FE-CAM-1": "data attribute has wrong datatype, "
                        "should be ndarray",
                    },
                    {
                        "PM-201-FE-CAM-1": "data attribute has wrong datatype, "
                        "should be uint16 or uint8",
                    },
                ],
                id="Image data invalid",
            ),
            pytest.param(
                {"waveform": {"x": "missing"}},
                [
                    {
                        "PM-201-HJ-PD": "x attribute is missing",
                    },
                ],
                None,
                id="Waveform x missing",
            ),
            pytest.param(
                {"waveform": {"x": 53}},
                [
                    {
                        "PM-201-HJ-PD": "x attribute must be a list of floats",
                    },
                ],
                [
                    {
                        "PM-201-HJ-PD": "x attribute must be a list of floats",
                    },
                    {"PM-201-HJ-PD": "x attribute has wrong shape"},
                ],
                id="Waveform x invalid",
            ),
            pytest.param(
                {"waveform": {"y": "missing"}},
                [
                    {
                        "PM-201-HJ-PD": "y attribute is missing",
                    },
                ],
                None,
                id="Waveform y missing",
            ),
            pytest.param(
                {"waveform": {"y": 53}},
                [
                    {
                        "PM-201-HJ-PD": "y attribute must be a list of floats",
                    },
                ],
                [
                    {
                        "PM-201-HJ-PD": "y attribute must be a list of floats",
                    },
                    {"PM-201-HJ-PD": "y attribute has wrong shape"},
                ],
                id="Waveform y invalid",
            ),
            pytest.param(
                {
                    "scalar": {"data": "missing"},
                    "image": {"data": 876},
                    "waveform": {"x": "missing", "y": "missing"},
                },
                [
                    {
                        "PM-201-FE-CAM-1": "data attribute has wrong datatype, "
                        "should be ndarray",
                    },
                    {"PM-201-FE-EM": "data attribute is missing"},
                    {"PM-201-HJ-PD": "x attribute is missing"},
                    {"PM-201-HJ-PD": "y attribute is missing"},
                ],
                [
                    {
                        "PM-201-FE-CAM-1": "data attribute has wrong datatype, "
                        "should be ndarray",
                    },
                    {
                        "PM-201-FE-CAM-1": "data attribute has wrong datatype, "
                        "should be uint16 or uint8",
                    },
                    {"PM-201-FE-EM": "data attribute is missing"},
                    {"PM-201-HJ-PD": "x attribute is missing"},
                    {"PM-201-HJ-PD": "y attribute is missing"},
                ],
                id="Mixed failed required attributes",
            ),
            pytest.param(
                "double_waveform",
                [],
                [
                    {
                        "FALSE_WAVEFORM": "Channel name is not recognised (does "
                        "not appear in manifest)",
                    },
                ],
                id="Two waveforms present test",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_required_attribute(
        self,
        remove_hdf_file,
        required_attributes,
        response,
        extra,
    ):
        if required_attributes == "double_waveform":
            hdf_tuple = await create_test_hdf_file(channel_name=["waveform"])
        else:
            hdf_tuple = await create_test_hdf_file(
                required_attributes=required_attributes,
            )

        channel_checker = ChannelChecks(*hdf_tuple)
        manifest = await ChannelManifest.get_most_recent_manifest()
        channel_checker.set_channels(manifest)

        channel_response = create_channel_response(response, extra)
        assert await channel_checker.channel_checks() == channel_response
        assert channel_checker.required_attribute_checks() == response

    @pytest.mark.parametrize(
        "optional_attributes, response",
        [
            pytest.param(
                {"scalar": {"units": "invalid"}},
                [
                    {
                        "PM-201-PA2-EM": "units attribute has wrong datatype",
                    },
                ],
                id="Scalar units invalid",
            ),
            pytest.param(
                {"image": {"exposure_time_s": "invalid"}},
                [
                    {
                        "PM-201-FE-CAM-1": "exposure_time_s attribute has "
                        "wrong datatype",
                    },
                ],
                id="Image exposure_time_s invalid",
            ),
            pytest.param(
                {"image": {"gain": "invalid"}},
                [
                    {
                        "PM-201-FE-CAM-1": "gain attribute has wrong datatype",
                    },
                ],
                id="Image gain invalid",
            ),
            pytest.param(
                {"image": {"x_pixel_size": "invalid"}},
                [
                    {
                        "PM-201-FE-CAM-1": "x_pixel_size attribute has wrong datatype",
                    },
                ],
                id="Image x_pixel_size invalid",
            ),
            pytest.param(
                {"image": {"x_pixel_units": "invalid"}},
                [
                    {
                        "PM-201-FE-CAM-1": "x_pixel_units attribute has wrong datatype",
                    },
                ],
                id="Image x_pixel_units invalid",
            ),
            pytest.param(
                {"image": {"y_pixel_size": "invalid"}},
                [
                    {
                        "PM-201-FE-CAM-1": "y_pixel_size attribute has wrong datatype",
                    },
                ],
                id="Image y_pixel_size invalid",
            ),
            pytest.param(
                {"image": {"y_pixel_units": "invalid"}},
                [
                    {
                        "PM-201-FE-CAM-1": "y_pixel_units attribute has wrong datatype",
                    },
                ],
                id="Image y_pixel_units invalid",
            ),
            pytest.param(
                {"waveform": {"x_units": "invalid"}},
                [
                    {
                        "PM-201-HJ-PD": "x_units attribute has wrong datatype",
                    },
                ],
                id="Waveform x_units invalid",
            ),
            pytest.param(
                {"waveform": {"y_units": "invalid"}},
                [
                    {
                        "PM-201-HJ-PD": "y_units attribute has wrong datatype",
                    },
                ],
                id="Waveform y_units invalid",
            ),
            pytest.param(
                {
                    "scalar": {"units": "invalid"},
                    "image": {
                        "y_pixel_size": "invalid",
                        "exposure_time_s": "invalid",
                        "gain": "invalid",
                    },
                    "waveform": {"x_units": "invalid", "y_units": "invalid"},
                },
                [
                    {"PM-201-FE-CAM-1": "exposure_time_s attribute has wrong datatype"},
                    {"PM-201-FE-CAM-1": "gain attribute has wrong datatype"},
                    {"PM-201-FE-CAM-1": "y_pixel_size attribute has wrong datatype"},
                    {"PM-201-HJ-PD": "x_units attribute has wrong datatype"},
                    {"PM-201-HJ-PD": "y_units attribute has wrong datatype"},
                    {"PM-201-PA2-EM": "units attribute has wrong datatype"},
                ],
                id="Mixed invalid optional attributes",
            ),
            pytest.param(
                {"image": {"bit_depth": "invalid"}},
                [{"PM-201-FE-CAM-1": "bit_depth attribute has wrong datatype"}],
                id="Invalid bit_depth",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_optional_attribute_fail(
        self,
        remove_hdf_file,
        optional_attributes,
        response,
    ):
        hdf_tuple = await create_test_hdf_file(optional_attributes=optional_attributes)
        channel_checker = ChannelChecks(*hdf_tuple)
        manifest = await ChannelManifest.get_most_recent_manifest()
        channel_checker.set_channels(manifest)

        channel_response = create_channel_response(response)
        assert await channel_checker.channel_checks() == channel_response
        assert channel_checker.optional_dtype_checks() == response

    @pytest.mark.parametrize(
        "required_attributes, response, extra",
        [
            pytest.param(
                {"scalar": {"data": ["list"]}},
                [
                    {
                        "PM-201-FE-EM": "data has wrong datatype",
                    },
                ],
                None,
                id="Scalar data invalid",
            ),
            pytest.param(
                {"image": {"data": 6780}},
                [
                    {
                        "PM-201-FE-CAM-1": "data attribute has wrong datatype, "
                        "should be uint16 or uint8",
                    },
                ],
                [
                    {
                        "PM-201-FE-CAM-1": "data attribute has wrong datatype, "
                        "should be ndarray",
                    },
                    {
                        "PM-201-FE-CAM-1": "data attribute has wrong datatype, "
                        "should be uint16 or uint8",
                    },
                ],
                id="Image data not a NumPy array",
            ),
            pytest.param(
                {"image": {"data": np.array([[1, 2, 3], [4, 5, 6]])}},
                [
                    {
                        "PM-201-FE-CAM-1": "data attribute has wrong datatype, "
                        "should be uint16 or uint8",
                    },
                ],
                None,
                id="Image data NumPy array but not uint8 or uint16",
            ),
            pytest.param(
                {"image": {"data": np.array([1, 2, 3], dtype=np.uint8)}},
                [
                    {
                        "PM-201-FE-CAM-1": "data attribute has wrong shape",
                    },
                ],
                None,
                id="Image data has wrong inner structure",
            ),
            pytest.param(
                {"waveform": {"x": "lgf"}},
                [
                    {"PM-201-HJ-PD": "x attribute has wrong shape"},
                ],
                [
                    {
                        "PM-201-HJ-PD": "x attribute must be a list of floats",
                    },
                    {"PM-201-HJ-PD": "x attribute has wrong shape"},
                ],
                id="Waveform x attribute has wrong shape (not a list)",
            ),
            pytest.param(
                {"waveform": {"y": 8765}},
                [
                    {"PM-201-HJ-PD": "y attribute has wrong shape"},
                ],
                [
                    {
                        "PM-201-HJ-PD": "y attribute must be a list of floats",
                    },
                    {"PM-201-HJ-PD": "y attribute has wrong shape"},
                ],
                id="Waveform y attribute has wrong shape (not a list)",
            ),
            pytest.param(
                {"waveform": {"x": ["lgf"]}},
                [
                    {
                        "PM-201-HJ-PD": "x attribute has wrong datatype, should "
                        "be a list of floats",
                    },
                ],
                [
                    {
                        "PM-201-HJ-PD": "x attribute must be a list of floats",
                    },
                    {
                        "PM-201-HJ-PD": "x attribute has wrong datatype, should "
                        "be a list of floats",
                    },
                ],
                id="Waveform x attribute has wrong data type",
            ),
            pytest.param(
                {"waveform": {"y": ["8765"]}},
                [
                    {
                        "PM-201-HJ-PD": "y attribute has wrong datatype, should "
                        "be a list of floats",
                    },
                ],
                [
                    {
                        "PM-201-HJ-PD": "y attribute must be a list of floats",
                    },
                    {
                        "PM-201-HJ-PD": "y attribute has wrong datatype, should "
                        "be a list of floats",
                    },
                ],
                id="Waveform y attribute has wrong data type",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_dataset_checks_fail(
        self,
        remove_hdf_file,
        required_attributes,
        response,
        extra,
    ):
        hdf_tuple = await create_test_hdf_file(required_attributes=required_attributes)
        channel_checker = ChannelChecks(*hdf_tuple)
        manifest = await ChannelManifest.get_most_recent_manifest()
        channel_checker.set_channels(manifest)

        channel_response = create_channel_response(response, extra)
        assert await channel_checker.channel_checks() == channel_response
        assert channel_checker.dataset_checks() == response

    @pytest.mark.parametrize(
        "unrecognised_attribute, response",
        [
            pytest.param(
                {"scalar": ["dataset"]},
                [
                    {
                        "PM-201-FE-CAM-2-CENY": "unexpected group or "
                        "dataset in channel group",
                    },
                ],
                id="Scalar unexpected dataset",
            ),
            pytest.param(
                {"scalar": ["group"]},
                [
                    {
                        "PM-201-FE-CAM-2-CENY": "unexpected group or "
                        "dataset in channel group",
                    },
                ],
                id="Scalar unexpected group",
            ),
            pytest.param(
                {"scalar": ["dataset", "group"]},
                [
                    {
                        "PM-201-FE-CAM-2-CENY": "unexpected group or "
                        "dataset in channel group",
                    },
                ],
                id="Scalar unexpected group and dataset",
            ),
            pytest.param(
                {"image": ["dataset"]},
                [
                    {
                        "PM-201-FE-CAM-1": "unexpected group or "
                        "dataset in channel group",
                    },
                ],
                id="Image unexpected dataset",
            ),
            pytest.param(
                {"image": ["group"]},
                [
                    {
                        "PM-201-FE-CAM-1": "unexpected group or "
                        "dataset in channel group",
                    },
                ],
                id="Image unexpected group",
            ),
            pytest.param(
                {"image": ["dataset", "group"]},
                [
                    {
                        "PM-201-FE-CAM-1": "unexpected group or "
                        "dataset in channel group",
                    },
                ],
                id="Image unexpected group and dataset",
            ),
            pytest.param(
                {"waveform": ["dataset2"]},
                [
                    {
                        "PM-201-HJ-PD": "unexpected group or "
                        "dataset in channel group",
                    },
                ],
                id="Waveform unexpected dataset",
            ),
            pytest.param(
                {"waveform": ["group2"]},
                [
                    {
                        "PM-201-HJ-PD": "unexpected group or "
                        "dataset in channel group",
                    },
                ],
                id="Waveform unexpected group",
            ),
            pytest.param(
                {"waveform": ["dataset1", "dataset2", "group1", "group2"]},
                [
                    {
                        "PM-201-HJ-PD": "unexpected group or "
                        "dataset in channel group",
                    },
                ],
                id="Waveform multiple unexpected values",
            ),
            pytest.param(
                {
                    "scalar": ["dataset", "group"],
                    "image": ["dataset", "group"],
                    "waveform": ["dataset1", "dataset2", "group1", "group2"],
                },
                [
                    {
                        "PM-201-FE-CAM-1": "unexpected group or "
                        "dataset in channel group",
                    },
                    {
                        "PM-201-FE-CAM-2-CENY": "unexpected group or "
                        "dataset in channel group",
                    },
                    {
                        "PM-201-HJ-PD": "unexpected group or "
                        "dataset in channel group",
                    },
                ],
                id="Multiple unexpected values",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_unrecognised_attribute_fail(
        self,
        remove_hdf_file,
        unrecognised_attribute,
        response,
    ):
        hdf_tuple = await create_test_hdf_file(
            unrecognised_attribute=unrecognised_attribute,
        )
        channel_checker = ChannelChecks(*hdf_tuple)
        manifest = await ChannelManifest.get_most_recent_manifest()
        channel_checker.set_channels(manifest)

        channel_response = create_channel_response(response)
        assert await channel_checker.channel_checks() == channel_response
        assert channel_checker.unrecognised_attribute_checks() == response

    @pytest.mark.parametrize(
        "channel_name, response",
        [
            pytest.param(
                ["scalar"],
                [
                    {
                        "FALSE_SCALAR": "Channel name is not recognised "
                        "(does not appear in manifest)",
                    },
                ],
                id="Unknown scalar name",
            ),
            pytest.param(
                ["image"],
                [
                    {
                        "FALSE_IMAGE": "Channel name is not recognised "
                        "(does not appear in manifest)",
                    },
                ],
                id="Unknown image name",
            ),
            pytest.param(
                ["waveform"],
                [
                    {
                        "FALSE_WAVEFORM": "Channel name is not recognised "
                        "(does not appear in manifest)",
                    },
                ],
                id="Unknown waveform name",
            ),
            pytest.param(
                ["scalar", "image", "waveform"],
                [
                    {
                        "FALSE_IMAGE": "Channel name is not recognised "
                        "(does not appear in manifest)",
                    },
                    {
                        "FALSE_SCALAR": "Channel name is not recognised "
                        "(does not appear in manifest)",
                    },
                    {
                        "FALSE_WAVEFORM": "Channel name is not recognised "
                        "(does not appear in manifest)",
                    },
                ],
                id="Unknown image, scalar and waveform names",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_channel_name_fail(
        self,
        remove_hdf_file,
        channel_name,
        response,
    ):
        hdf_tuple = await create_test_hdf_file(channel_name=channel_name)
        channel_checker = ChannelChecks(*hdf_tuple)
        manifest = await ChannelManifest.get_most_recent_manifest()
        channel_checker.set_channels(manifest)

        channel_response = create_channel_response(response)
        assert await channel_checker.channel_checks() == channel_response
        assert await channel_checker.channel_name_check() == response

    @pytest.mark.parametrize(
        "channel_dtype, required_attributes, optional_attributes, "
        "unrecognised_attribute, channel_name, channels_check, response",
        [
            pytest.param(
                ["scalar", "missing", "scalar"],
                {
                    "scalar": {"data": "missing"},
                    "image": {
                        "image_path": "missing",
                        "path": "missing",
                        "data": "missing",
                    },
                    "waveform": {
                        "waveform_path": "missing",
                        "path": "missing",
                        "x": "missing",
                        "y": "missing",
                    },
                },
                {
                    "scalar": {"units": "invalid"},
                    "image": {
                        "exposure_time_s": "invalid",
                        "gain": "invalid",
                        "x_pixel_size": "invalid",
                        "x_pixel_units": "invalid",
                        "y_pixel_size": "invalid",
                        "y_pixel_units": "invalid",
                    },
                    "waveform": {
                        "x_units": "invalid",
                        "y_units": "invalid",
                    },
                },
                {
                    "scalar": ["dataset", "group"],
                    "image": ["dataset", "group"],
                    "waveform": ["dataset1", "dataset2", "group1", "group2"],
                },
                ["scalar", "image", "waveform"],
                True,
                [
                    {"PM-201-FE-CAM-2-CENX": "channel_dtype attribute is missing"},
                    {"PM-201-FE-EM": "data attribute is missing"},
                    {"PM-201-PA2-EM": "units attribute has wrong datatype"},
                    {
                        "PM-201-FE-CAM-2-CENY": "unexpected group or dataset "
                        "in channel group",
                    },
                    {"PM-201-FE-CAM-1": "unexpected group or dataset in channel group"},
                    {
                        "PM-201-HJ-PD": "unexpected group or dataset "
                        "in channel group",
                    },
                    {
                        "ALL_FALSE_SCALAR": "Channel name is not recognised "
                        "(does not appear in manifest)",
                    },
                    {
                        "FALSE_IMAGE": "Channel name is not recognised "
                        "(does not appear in manifest)",
                    },
                    {
                        "FALSE_SCALAR": "Channel name is not recognised "
                        "(does not appear in manifest)",
                    },
                    {
                        "FALSE_WAVEFORM": "Channel name is not recognised "
                        "(does not appear in manifest)",
                    },
                ],
                id="Large mix of fails",
            ),
            pytest.param(
                None,
                None,
                None,
                None,
                None,
                False,
                [],
                id="All pass",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_channel_checks_separate(
        self,
        remove_hdf_file,
        channel_dtype,
        required_attributes,
        optional_attributes,
        unrecognised_attribute,
        channel_name,
        channels_check,
        response,
    ):
        hdf_tuple = await create_test_hdf_file(
            channel_dtype=channel_dtype,
            required_attributes=required_attributes,
            optional_attributes=optional_attributes,
            unrecognised_attribute=unrecognised_attribute,
            channel_name=channel_name,
            channels_check=channels_check,
        )
        channel_checker = ChannelChecks(*hdf_tuple)
        manifest = await ChannelManifest.get_most_recent_manifest()
        channel_checker.set_channels(manifest)

        channel_response = create_channel_response(response, channels=channels_check)
        assert await channel_checker.channel_checks() == channel_response

    @pytest.mark.parametrize(
        "test_type, response",
        [
            pytest.param(
                "test1",
                [
                    {
                        "FALSE_SCALAR": "Channel name is not recognised "
                        "(does not appear in manifest)",
                    },
                ],
                id="Scalar name and dtype fail",
            ),
            pytest.param(
                "test2",
                [
                    {"PM-201-FE-CAM-1": "x_pixel_size attribute has wrong datatype"},
                    {"PM-201-FE-CAM-1": "x_pixel_units attribute has wrong datatype"},
                    {
                        "PM-201-FE-CAM-1": "data attribute has wrong datatype, "
                        "should be uint16 or uint8",
                    },
                ],
                id="Image required and optional attributes fail",
            ),
            pytest.param(
                "test3",
                [
                    {
                        "PM-201-HJ-PD": "y attribute must be a list of floats",
                    },
                    {
                        "PM-201-HJ-PD": "x_units attribute has wrong datatype",
                    },
                    {
                        "PM-201-HJ-PD": "y attribute has wrong shape",
                    },
                ],
                id="Waveform optional attributes and dataset fail",
            ),
            pytest.param(
                "test4",
                [
                    {
                        "PM-201-FE-CAM-1": "unexpected group or dataset in "
                        "channel group",
                    },
                ],
                id="Image optional attribute, unrecognised attribute and dataset fail",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_channel_checks_fail(
        self,
        remove_hdf_file,
        test_type,
        response,
    ):
        hdf_tuple = await create_test_hdf_file(test_type=test_type)
        channel_checker = ChannelChecks(*hdf_tuple)
        manifest = await ChannelManifest.get_most_recent_manifest()
        channel_checker.set_channels(manifest)

        channel_response = create_channel_response(response)
        assert await channel_checker.channel_checks() == channel_response

    @pytest.mark.parametrize(
        ["possible_model"],
        [
            pytest.param({}),
            pytest.param(ScalarChannelMetadataModel(channel_dtype="scalar")),
        ],
    )
    def test_ensure_dict(self, possible_model: dict | BaseModel):
        ensured_dict = ChannelChecks._ensure_dict(possible_model)
        assert isinstance(ensured_dict, dict)
