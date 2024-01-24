import copy

import h5py
import numpy as np
import pytest

from operationsgateway_api.src.exceptions import (
    ModelError,
    RejectFileError,
    RejectRecordError,
)
from operationsgateway_api.src.records import ingestion_validator
from operationsgateway_api.src.records.hdf_handler import HDFDataHandler

# poetry run pytest -s "test/records/test_HDF_file.py" -v -vv


def generate_channel_check_block(record, test_type):
    if test_type == "test1":
        false_scalar = record.create_group("FALSE_SCALAR")
        false_scalar.attrs.create("channel_dtype", "thing")
        false_scalar.attrs.create("units", "ms")
        false_scalar.create_dataset("data", data=45)

    if test_type == "test2":
        n_comp_ff_image = record.create_group("N_COMP_FF_IMAGE")
        n_comp_ff_image.attrs.create("channel_dtype", "image")
        n_comp_ff_image.attrs.create("exposure_time_s", 0.001)
        n_comp_ff_image.attrs.create("gain", 5.5)
        n_comp_ff_image.attrs.create("x_pixel_size", "441")
        n_comp_ff_image.attrs.create("x_pixel_units", 42)
        n_comp_ff_image.attrs.create("y_pixel_size", 441.0)
        n_comp_ff_image.attrs.create("y_pixel_units", "µm")
        # example 2D dataset
        data = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]], dtype=np.uint32)
        n_comp_ff_image.create_dataset("data", data=data)

    if test_type == "test3":
        n_comp_spec_trace = record.create_group("N_COMP_SPEC_TRACE")
        n_comp_spec_trace.attrs.create("channel_dtype", "waveform")
        n_comp_spec_trace.attrs.create("x_units", 23)
        n_comp_spec_trace.attrs.create("y_units", "kJ")
        x = [1, 2, 3, 4, 5, 6]
        n_comp_spec_trace.create_dataset("x", data=x)
        n_comp_spec_trace.create_dataset("y", data=6)

    if test_type == "test4":
        n_comp_ff_image = record.create_group("N_COMP_FF_IMAGE")
        n_comp_ff_image.create_group("unrecognised_group")
        n_comp_ff_image.attrs.create("channel_dtype", "image")
        n_comp_ff_image.attrs.create("exposure_time_s", 0.001)
        n_comp_ff_image.attrs.create("gain", 5.5)
        n_comp_ff_image.attrs.create("x_pixel_size", "441.0")
        n_comp_ff_image.attrs.create("x_pixel_units", 456)
        n_comp_ff_image.attrs.create("y_pixel_size", 441.0)
        n_comp_ff_image.attrs.create("y_pixel_units", "µm")
        n_comp_ff_image.create_dataset("unrecognised_dataset", data=4)


async def create_test_hdf_file(
    data_version=None,
    timestamp=None,
    active_area=None,
    shotnum=None,
    active_experiment=None,
    channel_dtype=None,
    required_attributes=None,
    optional_attributes=None,
    unrecognised_attribute=None,
    channel_name=None,
    channels_check=False,
    test_type=None,
):

    data_version = data_version if data_version is not None else ["1.0", "exists"]
    timestamp = (
        timestamp if timestamp is not None else ["2022-04-07 14:28:16", "exists"]
    )
    active_area = active_area if active_area is not None else ["ea1", "exists"]
    shotnum = shotnum if shotnum is not None else ["valid", "exists"]
    active_experiment = (
        active_experiment if active_experiment is not None else ["90097341", "exists"]
    )
    channel_dtype = channel_dtype if channel_dtype is not None else []

    scalar_1_channel_dtype = None
    scalar_2_channel_dtype = None
    image_channel_dtype = None
    waveform_channel_dtype = None

    if len(channel_dtype) == 4:
        scalar_1_channel_dtype = channel_dtype[0]
        scalar_2_channel_dtype = channel_dtype[1]
        image_channel_dtype = channel_dtype[2]
        waveform_channel_dtype = channel_dtype[3]

    elif len(channel_dtype) == 0:
        pass

    else:
        channel = channel_dtype[2]
        if channel == "scalar":
            scalar_1_channel_dtype = channel_dtype[:2]
        if channel == "image":
            image_channel_dtype = channel_dtype[:2]
        if channel == "waveform":
            waveform_channel_dtype = channel_dtype[:2]

    hdf_file_path = "test.h5"
    with h5py.File("test.h5", "w") as f:

        if data_version[1] == "exists":
            f.attrs.create("epac_ops_data_version", data_version[0])
        record = f["/"]

        if timestamp[1] == "exists":
            record.attrs.create("timestamp", timestamp[0])

        if shotnum[1] == "exists":
            if shotnum[0] == "invalid":
                record.attrs.create("shotnum", "string")
            else:
                record.attrs.create("shotnum", 366272, dtype="u8")

        if active_area[1] == "exists":
            record.attrs.create("active_area", active_area[0])

        if active_experiment[1] == "exists":
            record.attrs.create("active_experiment", active_experiment[0])

        if test_type:
            generate_channel_check_block(record, test_type)

        gem_shot_num_value = record.create_group("GEM_SHOT_NUM_VALUE")
        gem_shot_num_value.attrs.create("channel_dtype", "scalar")
        if required_attributes and "scalar" in required_attributes:
            scalar = required_attributes["scalar"]
            if scalar["data"] != "missing":
                gem_shot_num_value.create_dataset("data", data=(scalar["data"]))
        else:
            gem_shot_num_value.create_dataset("data", data=366272)

        gem_shot_source_string = record.create_group("GEM_SHOT_SOURCE_STRING")
        if scalar_1_channel_dtype is not None:
            if scalar_1_channel_dtype[1] == "exists":
                gem_shot_source_string.attrs.create(
                    "channel_dtype",
                    scalar_1_channel_dtype[0],
                )
        else:
            gem_shot_source_string.attrs.create("channel_dtype", "scalar")
        gem_shot_source_string.create_dataset("data", data="EX")

        gem_shot_type_string = record.create_group("GEM_SHOT_TYPE_STRING")
        if scalar_2_channel_dtype is not None:
            if scalar_2_channel_dtype[1] == "exists":
                gem_shot_type_string.attrs.create(
                    "channel_dtype",
                    scalar_2_channel_dtype[0],
                )
        else:
            gem_shot_type_string.attrs.create("channel_dtype", "scalar")
        gem_shot_type_string.create_dataset("data", data="FP")

        if channel_name and "scalar" in channel_name:
            false_scalar = record.create_group("FALSE_SCALAR")
            false_scalar.attrs.create("channel_dtype", "scalar")
            false_scalar.attrs.create("units", "ms")
            false_scalar.create_dataset("data", data=45)

        if channel_name and "image" in channel_name:
            false_image = record.create_group("FALSE_IMAGE")
            false_image.attrs.create("channel_dtype", "image")
            false_image.attrs.create("exposure_time_s", 0.001)
            false_image.attrs.create("gain", 5.5)
            false_image.attrs.create("x_pixel_size", 441.0)
            false_image.attrs.create("x_pixel_units", "µm")
            false_image.attrs.create("y_pixel_size", 441.0)
            false_image.attrs.create("y_pixel_units", "µm")
            # example 2D dataset
            data = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]], dtype=np.uint16)
            false_image.create_dataset("data", data=data)

        if channel_name and "waveform" in channel_name:
            false_waveform = record.create_group("FALSE_WAVEFORM")
            false_waveform.attrs.create("channel_dtype", "waveform")
            false_waveform.attrs.create("x_units", "s")
            false_waveform.attrs.create("y_units", "kJ")
            x = [1, 2, 3, 4, 5, 5456]
            y = [8, 3, 6, 2, 3, 8, 425]
            false_waveform.create_dataset("x", data=x)
            false_waveform.create_dataset("y", data=y)

        n_comp_nf_image = record.create_group("N_COMP_NF_IMAGE")
        n_comp_nf_image.attrs.create("channel_dtype", "image")
        n_comp_nf_image.attrs.create("exposure_time_s", 0.001)
        n_comp_nf_image.attrs.create("gain", 5.5)
        n_comp_nf_image.attrs.create("x_pixel_size", 441.0)
        n_comp_nf_image.attrs.create("x_pixel_units", "µm")
        n_comp_nf_image.attrs.create("y_pixel_size", 441.0)
        n_comp_nf_image.attrs.create("y_pixel_units", "µm")
        data = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]], dtype=np.uint16)
        n_comp_nf_image.create_dataset("data", data=data)

        gem_wp_pos_value = record.create_group("GEM_WP_POS_VALUE")
        if (
            unrecognised_attribute
            and "scalar" in unrecognised_attribute
            and "group" in unrecognised_attribute["scalar"]
        ):
            gem_wp_pos_value.create_group("unrecognised_group")
        gem_wp_pos_value.attrs.create("channel_dtype", "scalar")
        gem_wp_pos_value.attrs.create("units", "ms")
        if (
            unrecognised_attribute
            and "scalar" in unrecognised_attribute
            and "dataset" in unrecognised_attribute["scalar"]
        ):
            gem_wp_pos_value.create_dataset("unrecognised_dataset", data=35)
        gem_wp_pos_value.create_dataset("data", data=45)

        n_comp_calculatede_value = record.create_group("N_COMP_CALCULATEDE_VALUE")
        n_comp_calculatede_value.attrs.create("channel_dtype", "scalar")
        n_comp_calculatede_value.attrs.create("units", "mm")
        n_comp_calculatede_value.create_dataset("data", data=10.84)

        n_comp_ff_e = record.create_group("N_COMP_FF_E")
        n_comp_ff_e.attrs.create("channel_dtype", "scalar")
        n_comp_ff_e.attrs.create("units", "mg")
        n_comp_ff_e.create_dataset("data", data=-8895000.0)

        if test_type != "test2" and test_type != "test4":
            n_comp_ff_image = record.create_group("N_COMP_FF_IMAGE")
            if (
                unrecognised_attribute
                and "image" in unrecognised_attribute
                and "group" in unrecognised_attribute["image"]
            ):
                n_comp_ff_image.create_group("unrecognised_group")
            if image_channel_dtype is not None:
                if image_channel_dtype[1] == "exists":
                    n_comp_ff_image.attrs.create(
                        "channel_dtype",
                        image_channel_dtype[0],
                    )
            else:
                n_comp_ff_image.attrs.create("channel_dtype", "image")
            if optional_attributes and "image" in optional_attributes:
                image = optional_attributes["image"]
                if "exposure_time_s" in image:
                    if image["exposure_time_s"] == "invalid":
                        n_comp_ff_image.attrs.create("exposure_time_s", "0.001")
                else:
                    n_comp_ff_image.attrs.create("exposure_time_s", 0.001)
                if "gain" in image:
                    if image["gain"] == "invalid":
                        n_comp_ff_image.attrs.create("gain", "5.5")
                else:
                    n_comp_ff_image.attrs.create("gain", 5.5)
                if "x_pixel_size" in image:
                    if image["x_pixel_size"] == "invalid":
                        n_comp_ff_image.attrs.create("x_pixel_size", "441.0")
                else:
                    n_comp_ff_image.attrs.create("x_pixel_size", 441.0)
                if "x_pixel_units" in image:
                    if image["x_pixel_units"] == "invalid":
                        n_comp_ff_image.attrs.create("x_pixel_units", 436)
                else:
                    n_comp_ff_image.attrs.create("x_pixel_units", "µm")
                if "y_pixel_size" in image:
                    if image["y_pixel_size"] == "invalid":
                        n_comp_ff_image.attrs.create("y_pixel_size", "441.0")
                else:
                    n_comp_ff_image.attrs.create("y_pixel_size", 441.0)
                if "y_pixel_units" in image:
                    if image["y_pixel_units"] == "invalid":
                        n_comp_ff_image.attrs.create("y_pixel_units", 346)
                else:
                    n_comp_ff_image.attrs.create("y_pixel_units", "µm")
            else:
                n_comp_ff_image.attrs.create("exposure_time_s", 0.001)
                n_comp_ff_image.attrs.create("gain", 5.5)
                n_comp_ff_image.attrs.create("x_pixel_size", 441.0)
                n_comp_ff_image.attrs.create("x_pixel_units", "µm")
                n_comp_ff_image.attrs.create("y_pixel_size", 441.0)
                n_comp_ff_image.attrs.create("y_pixel_units", "µm")
            # example 2D dataset
            if (
                unrecognised_attribute
                and "image" in unrecognised_attribute
                and "dataset" in unrecognised_attribute["image"]
            ):
                n_comp_ff_image.create_dataset("unrecognised_dataset", data=35)
            data = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]], dtype=np.uint16)
            if required_attributes and "image" in required_attributes:
                image = required_attributes["image"]
                if image["data"] != "missing":
                    n_comp_ff_image.create_dataset("data", data=(image["data"]))
            else:
                n_comp_ff_image.create_dataset("data", data=data)

        n_comp_ff_intergration = record.create_group("N_COMP_FF_INTEGRATION")
        n_comp_ff_intergration.attrs.create("channel_dtype", "scalar")
        if optional_attributes and "scalar" in optional_attributes:
            scalar = optional_attributes["scalar"]
            if scalar["units"] == "invalid":
                n_comp_ff_intergration.attrs.create("units", 764)
            else:
                n_comp_ff_intergration.attrs.create("units", "µm")
        else:
            n_comp_ff_intergration.attrs.create("units", "µm")
        n_comp_ff_intergration.create_dataset("data", data=8895000.0)

        n_comp_ff_xpos = record.create_group("N_COMP_FF_XPOS")
        n_comp_ff_xpos.attrs.create("channel_dtype", "scalar")
        n_comp_ff_xpos.attrs.create("units", "mm")
        n_comp_ff_xpos.create_dataset("data", data=330.523)

        if channels_check:
            n_comp_ff_ypos = record.create_group("ALL_FALSE_SCALAR")
            n_comp_ff_ypos.attrs.create("channel_dtype", "thing")
            n_comp_ff_ypos.attrs.create("units", 44)
            n_comp_ff_ypos.create_dataset("data", data=["data"])
            n_comp_ff_ypos.create_dataset("unrecognised_scalar_dataset", data=[32])
        else:
            n_comp_ff_ypos = record.create_group("N_COMP_FF_YPOS")
            n_comp_ff_ypos.attrs.create("channel_dtype", "scalar")
            n_comp_ff_ypos.attrs.create("units", "mm")
            n_comp_ff_ypos.create_dataset("data", data=243.771)

        n_comp_throughpute_value = record.create_group("N_COMP_THROUGHPUTE_VALUE")
        n_comp_throughpute_value.attrs.create("channel_dtype", "scalar")
        n_comp_throughpute_value.attrs.create("units", "cm")
        n_comp_throughpute_value.create_dataset("data", data=74)

        ta3_shot_num_value = record.create_group("TA3_SHOT_NUM_VALUE")
        ta3_shot_num_value.attrs.create("channel_dtype", "scalar")
        ta3_shot_num_value.create_dataset("data", data=217343.0)

        if test_type != "test3":
            n_comp_spec_trace = record.create_group("N_COMP_SPEC_TRACE")
            if (
                unrecognised_attribute
                and "waveform" in unrecognised_attribute
                and "group1" in unrecognised_attribute["waveform"]
            ):
                n_comp_spec_trace.create_group("unrecognised_group1")
            if (
                unrecognised_attribute
                and "waveform" in unrecognised_attribute
                and "group2" in unrecognised_attribute["waveform"]
            ):
                n_comp_spec_trace.create_group("unrecognised_group2")
            if waveform_channel_dtype is not None:
                if waveform_channel_dtype[1] == "exists":
                    n_comp_spec_trace.attrs.create(
                        "channel_dtype",
                        waveform_channel_dtype[0],
                    )
            else:
                n_comp_spec_trace.attrs.create("channel_dtype", "waveform")
            if optional_attributes and "waveform" in optional_attributes:
                waveform = optional_attributes["waveform"]
                if "x_units" in waveform:
                    if waveform["x_units"] == "invalid":
                        n_comp_spec_trace.attrs.create("x_units", 35)
                else:
                    n_comp_spec_trace.attrs.create("x_units", "s")
                if "y_units" in waveform:
                    if waveform["y_units"] == "invalid":
                        n_comp_spec_trace.attrs.create("y_units", 42)
                else:
                    n_comp_spec_trace.attrs.create("y_units", "kJ")
            else:
                n_comp_spec_trace.attrs.create("x_units", "s")
                n_comp_spec_trace.attrs.create("y_units", "kJ")
            x = [1, 2, 3, 4, 5, 6]
            y = [8, 3, 6, 2, 3, 8, 425]
            if required_attributes and "waveform" in required_attributes:
                waveform = required_attributes["waveform"]
                if "x" in waveform:
                    if waveform["x"] != "missing":
                        n_comp_spec_trace.create_dataset("x", data=(waveform["x"]))
                else:
                    n_comp_spec_trace.create_dataset("x", data=x)
                if "y" in waveform:
                    if waveform["y"] != "missing":
                        n_comp_spec_trace.create_dataset("y", data=(waveform["y"]))
                else:
                    n_comp_spec_trace.create_dataset("y", data=y)
            else:
                n_comp_spec_trace.create_dataset("x", data=x)
                n_comp_spec_trace.create_dataset("y", data=y)
            if (
                unrecognised_attribute
                and "waveform" in unrecognised_attribute
                and "dataset1" in unrecognised_attribute["waveform"]
            ):
                n_comp_spec_trace.create_dataset("unrecognised_dataset1", data=35)
            if (
                unrecognised_attribute
                and "waveform" in unrecognised_attribute
                and "dataset2" in unrecognised_attribute["waveform"]
            ):
                n_comp_spec_trace.create_dataset("unrecognised_dataset2", data=35)

        types = record.create_group("Type")
        types.attrs.create("channel_dtype", "scalar")
        types.create_dataset("data", data="GS")

    hdf_handler = HDFDataHandler(hdf_file_path)
    return await hdf_handler.extract_data()


def create_channel_response(responses, extra=None, channels=False):
    model_response = {
        "accepted channels": [
            "GEM_SHOT_NUM_VALUE",
            "GEM_SHOT_SOURCE_STRING",
            "GEM_SHOT_TYPE_STRING",
            "GEM_WP_POS_VALUE",
            "N_COMP_CALCULATEDE_VALUE",
            "N_COMP_FF_E",
            "N_COMP_FF_IMAGE",
            "N_COMP_FF_INTEGRATION",
            "N_COMP_FF_XPOS",
            "N_COMP_FF_YPOS",
            "N_COMP_NF_IMAGE",
            "N_COMP_SPEC_TRACE",
            "N_COMP_THROUGHPUTE_VALUE",
            "TA3_SHOT_NUM_VALUE",
            "Type",
        ],
        "rejected channels": {},
    }

    if extra:
        responses = extra

    if channels:
        model_response["accepted channels"].remove("N_COMP_FF_YPOS")

    for response in responses:
        for channel, message in response.items():
            if channel in model_response["accepted channels"]:
                model_response["accepted channels"].remove(channel)

            if channel not in model_response["rejected channels"]:
                model_response["rejected channels"][channel] = [message]
            else:
                if message not in model_response["rejected channels"][channel]:
                    (model_response["rejected channels"][channel]).extend([message])

    return model_response


# poetry run pytest -s "test/records/test_HDF_file.py::TestFile" -v -vv
class TestFile:
    @pytest.mark.asyncio
    async def test_file_checks_pass(self, remove_hdf_file):
        record_data, waveforms, images, _ = await create_test_hdf_file()
        file_checker = ingestion_validator.FileChecks(record_data)

        file_checker.epac_data_version_checks()

    @pytest.mark.asyncio
    async def test_minor_version_too_high(self, remove_hdf_file):
        record_data, waveforms, images, _ = await create_test_hdf_file(
            data_version=["1.4", "exists"],
        )
        file_checker = ingestion_validator.FileChecks(record_data)

        assert (
            file_checker.epac_data_version_checks()
            == "File minor version number too high (expected 0)"
        )

    @pytest.mark.parametrize(
        "data_version, match",
        [
            pytest.param(
                ["1.0", "missing"],
                "epac_ops_data_version does not exist",
                id="epac_ops_data_version is missing",
            ),
            pytest.param(
                [1.0, "exists"],
                "epac_ops_data_version has wrong datatype. Should be string",
                id="epac_ops_data_version wrong datatype",
            ),
            pytest.param(
                ["4.0", "exists"],
                "epac_ops_data_version major version was not 1",
                id="epac_ops_data_version unknown version",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_epac_ops_data_version_missing(
        self,
        data_version,
        match,
        remove_hdf_file,
    ):
        record_data, waveforms, images, _ = await create_test_hdf_file(
            data_version=data_version,
        )
        file_checker = ingestion_validator.FileChecks(record_data)

        with pytest.raises(RejectFileError, match=match):
            file_checker.epac_data_version_checks()


# poetry run pytest -s "test/records/test_HDF_file.py::TestRecord" -v -vv
class TestRecord:
    @pytest.mark.parametrize(
        "shotnum, active_experiment",
        [
            pytest.param(
                ["valid", "exists"],
                ["90097341", "exists"],
                id="all optional values present",
            ),
            pytest.param(
                ["valid", "exists"],
                ["90097341", "missing"],
                id="only shotnum present",
            ),
            pytest.param(
                ["valid", "missing"],
                ["90097341", "exists"],
                id="only active_experiment present",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_record_checks_pass(
        self,
        shotnum,
        active_experiment,
        remove_hdf_file,
    ):
        record_data, waveforms, images, _ = await create_test_hdf_file(
            shotnum=shotnum,
            active_experiment=active_experiment,
        )
        record_checker = ingestion_validator.RecordChecks(record_data)

        record_checker.active_area_checks()
        record_checker.optional_metadata_checks()

    @pytest.mark.parametrize(
        "active_area, shotnum, active_experiment, test, match",
        [
            pytest.param(
                ["ea1", "missing"],
                ["valid", "exists"],
                ["90097341", "exists"],
                "active_area",
                "active_area is missing",
                id="active_area is missing",
            ),
            pytest.param(
                [467, "exists"],
                ["valid", "exists"],
                ["90097341", "exists"],
                "active_area",
                "active_area has wrong datatype. Expected string",
                id="active_area wrong datatype",
            ),
            pytest.param(
                ["ea1", "exists"],
                ["invalid", "exists"],
                [90097341, "exists"],
                "other",
                "empty",
                id="shotnum and active_experiment have wrong datatype",
            ),
            pytest.param(
                ["ea1", "exists"],
                ["invalid", "exists"],
                ["90097341", "missing"],
                "other",
                "empty",
                id="shotnum has wrong datatype active_experiment missing",
            ),
            pytest.param(
                ["ea1", "exists"],
                ["valid", "missing"],
                [90097341, "exists"],
                "optional",
                "active_experiment has wrong datatype. Expected string",
                id="active_experiment has wrong datatype shotnum missing",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_record_checks_fail(
        self,
        active_area,
        shotnum,
        active_experiment,
        test,
        match,
        remove_hdf_file,
    ):
        if test == "other":
            with pytest.raises(ModelError):
                record_data, waveforms, images, _ = await create_test_hdf_file(
                    active_area=active_area,
                    shotnum=shotnum,
                    active_experiment=active_experiment,
                )
        else:
            record_data, waveforms, images, _ = await create_test_hdf_file(
                active_area=active_area,
                shotnum=shotnum,
                active_experiment=active_experiment,
            )
            record_checker = ingestion_validator.RecordChecks(record_data)

            with pytest.raises(RejectRecordError, match=match):
                if test == "timestamp":
                    record_checker.timestamp_checks()
                if test == "active_area":
                    record_checker.active_area_checks()
                if test == "optional":
                    record_checker.optional_metadata_checks()


# poetry run pytest -s "test/records/test_HDF_file.py::TestChannel" -v -vv
class TestChannel:
    @pytest.mark.asyncio
    async def test_channel_checks_success(self, remove_hdf_file):
        (
            record_data,
            waveforms,
            images,
            internal_failed_channel,
        ) = await create_test_hdf_file()

        channel_checker = ingestion_validator.ChannelChecks(
            record_data,
            waveforms,
            images,
            internal_failed_channel,
        )
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
            "accepted channels": [
                "GEM_SHOT_NUM_VALUE",
                "GEM_SHOT_SOURCE_STRING",
                "GEM_SHOT_TYPE_STRING",
                "GEM_WP_POS_VALUE",
                "N_COMP_CALCULATEDE_VALUE",
                "N_COMP_FF_E",
                "N_COMP_FF_IMAGE",
                "N_COMP_FF_INTEGRATION",
                "N_COMP_FF_XPOS",
                "N_COMP_FF_YPOS",
                "N_COMP_NF_IMAGE",
                "N_COMP_SPEC_TRACE",
                "N_COMP_THROUGHPUTE_VALUE",
                "TA3_SHOT_NUM_VALUE",
                "Type",
            ],
            "rejected channels": {},
        }

    @pytest.mark.parametrize(
        "altered_channel, response",
        [
            pytest.param(
                ["scalar", "missing", "scalar"],
                [
                    {
                        "GEM_SHOT_SOURCE_STRING": "channel_dtype attribute is "
                        "missing (cannot perform other checks without)",
                    },
                ],
                id="Scalar channel_dtype missing",
            ),
            pytest.param(
                ["image", "missing", "image"],
                [
                    {
                        "N_COMP_FF_IMAGE": "channel_dtype attribute is missing "
                        "(cannot perform other checks without)",
                    },
                ],
                id="Image channel_dtype missing",
            ),
            pytest.param(
                ["waveform", "missing", "waveform"],
                [
                    {
                        "N_COMP_SPEC_TRACE": "channel_dtype attribute is missing "
                        "(cannot perform other checks without)",
                    },
                ],
                id="Waveform channel_dtype missing",
            ),
            pytest.param(
                [487, "exists", "scalar"],
                [
                    {
                        "GEM_SHOT_SOURCE_STRING": "channel_dtype has wrong data "
                        "type or its value is unsupported",
                    },
                ],
                id="Scalar channel_dtype incorrect",
            ),
            pytest.param(
                ["487", "exists", "image"],
                [
                    {
                        "N_COMP_FF_IMAGE": "channel_dtype has wrong data type "
                        "or its value is unsupported",
                    },
                ],
                id="Image channel_dtype incorrect",
            ),
            pytest.param(
                ["None", "exists", "waveform"],
                [
                    {
                        "N_COMP_SPEC_TRACE": "channel_dtype has wrong data "
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
                    {
                        "GEM_SHOT_SOURCE_STRING": "channel_dtype has wrong data "
                        "type or its value is unsupported",
                    },
                    {
                        "GEM_SHOT_TYPE_STRING": "channel_dtype has wrong data "
                        "type or its value is unsupported",
                    },
                    {
                        "N_COMP_FF_IMAGE": "channel_dtype attribute is missing "
                        "(cannot perform other checks without)",
                    },
                    {
                        "N_COMP_SPEC_TRACE": "channel_dtype has wrong data type "
                        "or its value is unsupported",
                    },
                ],
                id="Multiple channel_dtype fails",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_channel_dtype_fail(self, remove_hdf_file, altered_channel, response):
        (
            record_data,
            waveforms,
            images,
            internal_failed_channel,
        ) = await create_test_hdf_file(channel_dtype=altered_channel)

        channel_checker = ingestion_validator.ChannelChecks(
            record_data,
            waveforms,
            images,
            internal_failed_channel,
        )

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
                        "GEM_SHOT_NUM_VALUE": "data attribute is missing",
                    },
                ],
                None,
                id="Scalar data missing",
            ),
            pytest.param(
                {"scalar": {"data": ["list type"]}},
                [
                    {
                        "GEM_SHOT_NUM_VALUE": "data has wrong datatype",
                    },
                ],
                None,
                id="Scalar data invalid",
            ),
            pytest.param(
                {"image": {"data": "missing"}},
                [
                    {
                        "N_COMP_FF_IMAGE": "data attribute is missing",
                    },
                ],
                None,
                id="Image data missing",
            ),
            pytest.param(
                {"image": {"data": 42}},
                [
                    {
                        "N_COMP_FF_IMAGE": "data attribute has wrong datatype, "
                        "should be ndarray",
                    },
                ],
                [
                    {
                        "N_COMP_FF_IMAGE": "data attribute has wrong datatype, "
                        "should be ndarray",
                    },
                    {
                        "N_COMP_FF_IMAGE": "data attribute has wrong datatype, "
                        "should be uint16 or uint8",
                    },
                ],
                id="Image data invalid",
            ),
            pytest.param(
                {"waveform": {"x": "missing"}},
                [
                    {
                        "N_COMP_SPEC_TRACE": "x attribute is missing",
                    },
                ],
                None,
                id="Waveform x missing",
            ),
            pytest.param(
                {"waveform": {"x": 53}},
                [
                    {
                        "N_COMP_SPEC_TRACE": "x attribute must be a list of floats",
                    },
                ],
                [
                    {
                        "N_COMP_SPEC_TRACE": "x attribute must be a list of floats",
                    },
                    {"N_COMP_SPEC_TRACE": "x attribute has wrong shape"},
                ],
                id="Waveform x invalid",
            ),
            pytest.param(
                {"waveform": {"y": "missing"}},
                [
                    {
                        "N_COMP_SPEC_TRACE": "y attribute is missing",
                    },
                ],
                None,
                id="Waveform y missing",
            ),
            pytest.param(
                {"waveform": {"y": 53}},
                [
                    {
                        "N_COMP_SPEC_TRACE": "y attribute must be a list of floats",
                    },
                ],
                [
                    {
                        "N_COMP_SPEC_TRACE": "y attribute must be a list of floats",
                    },
                    {"N_COMP_SPEC_TRACE": "y attribute has wrong shape"},
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
                        "N_COMP_FF_IMAGE": "data attribute has wrong datatype, "
                        "should be ndarray",
                    },
                    {"GEM_SHOT_NUM_VALUE": "data attribute is missing"},
                    {"N_COMP_SPEC_TRACE": "x attribute is missing"},
                    {"N_COMP_SPEC_TRACE": "y attribute is missing"},
                ],
                [
                    {
                        "N_COMP_FF_IMAGE": "data attribute has wrong datatype, "
                        "should be ndarray",
                    },
                    {
                        "N_COMP_FF_IMAGE": "data attribute has wrong datatype, "
                        "should be uint16 or uint8",
                    },
                    {"GEM_SHOT_NUM_VALUE": "data attribute is missing"},
                    {"N_COMP_SPEC_TRACE": "x attribute is missing"},
                    {"N_COMP_SPEC_TRACE": "y attribute is missing"},
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
            (
                record_data,
                waveforms,
                images,
                internal_failed_channel,
            ) = await create_test_hdf_file(channel_name=["waveform"])
        else:
            (
                record_data,
                waveforms,
                images,
                internal_failed_channel,
            ) = await create_test_hdf_file(required_attributes=required_attributes)

        channel_checker = ingestion_validator.ChannelChecks(
            record_data,
            waveforms,
            images,
            internal_failed_channel,
        )
        """
        required_attributes = {
            "scalar": {"data": "missing"},
            "image": {"image_path": "missing", "path": "missing", "data": "missing"},
            "waveform": {
                "waveform_id": "missing",
                "id_": "missing",
                "x": "missing",
                "y": "missing"
            },
        }
        """

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
                        "N_COMP_FF_INTEGRATION": "units attribute has wrong datatype",
                    },
                ],
                id="Scalar units invalid",
            ),
            pytest.param(
                {"image": {"exposure_time_s": "invalid"}},
                [
                    {
                        "N_COMP_FF_IMAGE": "exposure_time_s attribute has "
                        "wrong datatype",
                    },
                ],
                id="Image exposure_time_s invalid",
            ),
            pytest.param(
                {"image": {"gain": "invalid"}},
                [
                    {
                        "N_COMP_FF_IMAGE": "gain attribute has wrong datatype",
                    },
                ],
                id="Image gain invalid",
            ),
            pytest.param(
                {"image": {"x_pixel_size": "invalid"}},
                [
                    {
                        "N_COMP_FF_IMAGE": "x_pixel_size attribute has wrong datatype",
                    },
                ],
                id="Image x_pixel_size invalid",
            ),
            pytest.param(
                {"image": {"x_pixel_units": "invalid"}},
                [
                    {
                        "N_COMP_FF_IMAGE": "x_pixel_units attribute has wrong datatype",
                    },
                ],
                id="Image x_pixel_units invalid",
            ),
            pytest.param(
                {"image": {"y_pixel_size": "invalid"}},
                [
                    {
                        "N_COMP_FF_IMAGE": "y_pixel_size attribute has wrong datatype",
                    },
                ],
                id="Image y_pixel_size invalid",
            ),
            pytest.param(
                {"image": {"y_pixel_units": "invalid"}},
                [
                    {
                        "N_COMP_FF_IMAGE": "y_pixel_units attribute has wrong datatype",
                    },
                ],
                id="Image y_pixel_units invalid",
            ),
            pytest.param(
                {"waveform": {"x_units": "invalid"}},
                [
                    {
                        "N_COMP_SPEC_TRACE": "x_units attribute has wrong datatype",
                    },
                ],
                id="Waveform x_units invalid",
            ),
            pytest.param(
                {"waveform": {"y_units": "invalid"}},
                [
                    {
                        "N_COMP_SPEC_TRACE": "y_units attribute has wrong datatype",
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
                    {"N_COMP_FF_IMAGE": "exposure_time_s attribute has wrong datatype"},
                    {"N_COMP_FF_IMAGE": "gain attribute has wrong datatype"},
                    {"N_COMP_FF_IMAGE": "y_pixel_size attribute has wrong datatype"},
                    {"N_COMP_FF_INTEGRATION": "units attribute has wrong datatype"},
                    {"N_COMP_SPEC_TRACE": "x_units attribute has wrong datatype"},
                    {"N_COMP_SPEC_TRACE": "y_units attribute has wrong datatype"},
                ],
                id="Mixed invalid optional attributes",
            ),
            pytest.param(
                {"waveform": {"thumbnail": "invalid"}},
                [
                    {
                        "N_COMP_SPEC_TRACE": "thumbnail attribute has wrong datatype",
                    },
                ],
                id="Waveform thumbnail invalid",
            ),
            pytest.param(
                {"image": {"thumbnail": "invalid"}},
                [
                    {
                        "N_COMP_FF_IMAGE": "thumbnail attribute has wrong datatype",
                    },
                ],
                id="Image thumbnail invalid",
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
        (
            record_data,
            waveforms,
            images,
            internal_failed_channel,
        ) = await create_test_hdf_file(optional_attributes=optional_attributes)

        if "image" in optional_attributes:
            if "thumbnail" in optional_attributes["image"]:
                record_data.channels["N_COMP_FF_IMAGE"].thumbnail = 25
        if "waveform" in optional_attributes:
            if "thumbnail" in optional_attributes["waveform"]:
                record_data.channels["N_COMP_SPEC_TRACE"].thumbnail = 25

        channel_checker = ingestion_validator.ChannelChecks(
            record_data,
            waveforms,
            images,
            internal_failed_channel,
        )
        """
        optional_attributes = {
            "scalar": {"units": "invalid"},
            "image": {
                "exposure_time_s": "invalid",
                "gain": "invalid",
                "x_pixel_size": "invalid",
                "x_pixel_units": "invalid",
                "y_pixel_size": "invalid",
                "y_pixel_units": "invalid",
                "thumbnail": "invalid",
            },
            "waveform": {
                "x_units": "invalid",
                "y_units": "invalid",
                "thumbnail": "invalid"
            },
        }
        """

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
                        "GEM_SHOT_NUM_VALUE": "data has wrong datatype",
                    },
                ],
                None,
                id="Scalar data invalid",
            ),
            pytest.param(
                {"image": {"data": 6780}},
                [
                    {
                        "N_COMP_FF_IMAGE": "data attribute has wrong datatype, "
                        "should be uint16 or uint8",
                    },
                ],
                [
                    {
                        "N_COMP_FF_IMAGE": "data attribute has wrong datatype, "
                        "should be ndarray",
                    },
                    {
                        "N_COMP_FF_IMAGE": "data attribute has wrong datatype, "
                        "should be uint16 or uint8",
                    },
                ],
                id="Image data not a NumPy array",
            ),
            pytest.param(
                {"image": {"data": np.array([[1, 2, 3], [4, 5, 6]])}},
                [
                    {
                        "N_COMP_FF_IMAGE": "data attribute has wrong datatype, "
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
                        "N_COMP_FF_IMAGE": "data attribute has wrong shape",
                    },
                ],
                None,
                id="Image data has wrong inner structure",
            ),
            pytest.param(
                {"waveform": {"x": "lgf"}},
                [
                    {"N_COMP_SPEC_TRACE": "x attribute has wrong shape"},
                ],
                [
                    {
                        "N_COMP_SPEC_TRACE": "x attribute must be a list of floats",
                    },
                    {"N_COMP_SPEC_TRACE": "x attribute has wrong shape"},
                ],
                id="Waveform x attribute has wrong shape (not a list)",
            ),
            pytest.param(
                {"waveform": {"y": 8765}},
                [
                    {"N_COMP_SPEC_TRACE": "y attribute has wrong shape"},
                ],
                [
                    {
                        "N_COMP_SPEC_TRACE": "y attribute must be a list of floats",
                    },
                    {"N_COMP_SPEC_TRACE": "y attribute has wrong shape"},
                ],
                id="Waveform y attribute has wrong shape (not a list)",
            ),
            pytest.param(
                {"waveform": {"x": ["lgf"]}},
                [
                    {
                        "N_COMP_SPEC_TRACE": "x attribute has wrong datatype, should "
                        "be a list of floats",
                    },
                ],
                [
                    {
                        "N_COMP_SPEC_TRACE": "x attribute must be a list of floats",
                    },
                    {
                        "N_COMP_SPEC_TRACE": "x attribute has wrong datatype, should "
                        "be a list of floats",
                    },
                ],
                id="Waveform x attribute has wrong data type",
            ),
            pytest.param(
                {"waveform": {"y": ["8765"]}},
                [
                    {
                        "N_COMP_SPEC_TRACE": "y attribute has wrong datatype, should "
                        "be a list of floats",
                    },
                ],
                [
                    {
                        "N_COMP_SPEC_TRACE": "y attribute must be a list of floats",
                    },
                    {
                        "N_COMP_SPEC_TRACE": "y attribute has wrong datatype, should "
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
        (
            record_data,
            waveforms,
            images,
            internal_failed_channel,
        ) = await create_test_hdf_file(required_attributes=required_attributes)

        channel_checker = ingestion_validator.ChannelChecks(
            record_data,
            waveforms,
            images,
            internal_failed_channel,
        )
        """
        required_attributes = {
            "scalar": {"data": "missing"},
            "image": {"data": "missing"},
            "waveform": {
                "x": "missing",
                "y": "missing",
            },
        }
        """

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
                        "GEM_WP_POS_VALUE": "unexpected group or "
                        "dataset in channel group",
                    },
                ],
                id="Scalar unexpected dataset",
            ),
            pytest.param(
                {"scalar": ["group"]},
                [
                    {
                        "GEM_WP_POS_VALUE": "unexpected group or "
                        "dataset in channel group",
                    },
                ],
                id="Scalar unexpected group",
            ),
            pytest.param(
                {"scalar": ["dataset", "group"]},
                [
                    {
                        "GEM_WP_POS_VALUE": "unexpected group or "
                        "dataset in channel group",
                    },
                ],
                id="Scalar unexpected group and dataset",
            ),
            pytest.param(
                {"image": ["dataset"]},
                [
                    {
                        "N_COMP_FF_IMAGE": "unexpected group or "
                        "dataset in channel group",
                    },
                ],
                id="Image unexpected dataset",
            ),
            pytest.param(
                {"image": ["group"]},
                [
                    {
                        "N_COMP_FF_IMAGE": "unexpected group or "
                        "dataset in channel group",
                    },
                ],
                id="Image unexpected group",
            ),
            pytest.param(
                {"image": ["dataset", "group"]},
                [
                    {
                        "N_COMP_FF_IMAGE": "unexpected group or "
                        "dataset in channel group",
                    },
                ],
                id="Image unexpected group and dataset",
            ),
            pytest.param(
                {"waveform": ["dataset2"]},
                [
                    {
                        "N_COMP_SPEC_TRACE": "unexpected group or "
                        "dataset in channel group",
                    },
                ],
                id="Waveform unexpected dataset",
            ),
            pytest.param(
                {"waveform": ["group2"]},
                [
                    {
                        "N_COMP_SPEC_TRACE": "unexpected group or "
                        "dataset in channel group",
                    },
                ],
                id="Waveform unexpected group",
            ),
            pytest.param(
                {"waveform": ["dataset1", "dataset2", "group1", "group2"]},
                [
                    {
                        "N_COMP_SPEC_TRACE": "unexpected group or "
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
                        "GEM_WP_POS_VALUE": "unexpected group or "
                        "dataset in channel group",
                    },
                    {
                        "N_COMP_FF_IMAGE": "unexpected group or "
                        "dataset in channel group",
                    },
                    {
                        "N_COMP_SPEC_TRACE": "unexpected group or "
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
        (
            record_data,
            waveforms,
            images,
            internal_failed_channel,
        ) = await create_test_hdf_file(unrecognised_attribute=unrecognised_attribute)

        channel_checker = ingestion_validator.ChannelChecks(
            record_data,
            waveforms,
            images,
            internal_failed_channel,
        )
        """
            unrecognised_attribute = {
                "scalar": ["dataset", "group"]
                "image": ["dataset", "group"]
                "waveform": ["dataset1", "dataset2", "group1", "group2"]
            }
        """

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
                id="Unknown waveform name",
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
        (
            record_data,
            waveforms,
            images,
            internal_failed_channel,
        ) = await create_test_hdf_file(channel_name=channel_name)

        channel_checker = ingestion_validator.ChannelChecks(
            record_data,
            waveforms,
            images,
            internal_failed_channel,
        )
        """
        channel_name = [scalar, image, waveform]
        """

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
                        "waveform_id": "missing",
                        "id_": "missing",
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
                        "thumbnail": "invalid",
                    },
                    "waveform": {
                        "x_units": "invalid",
                        "y_units": "invalid",
                        "thumbnail": "invalid",
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
                    {
                        "GEM_SHOT_SOURCE_STRING": "channel_dtype attribute is missing "
                        "(cannot perform other checks without)",
                    },
                    {"GEM_SHOT_NUM_VALUE": "data attribute is missing"},
                    {"N_COMP_FF_INTEGRATION": "units attribute has wrong datatype"},
                    {
                        "GEM_WP_POS_VALUE": "unexpected group or dataset "
                        "in channel group",
                    },
                    {"N_COMP_FF_IMAGE": "unexpected group or dataset in channel group"},
                    {
                        "N_COMP_SPEC_TRACE": "unexpected group or dataset "
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
        (
            record_data,
            waveforms,
            images,
            internal_failed_channel,
        ) = await create_test_hdf_file(
            channel_dtype=channel_dtype,
            required_attributes=required_attributes,
            optional_attributes=optional_attributes,
            unrecognised_attribute=unrecognised_attribute,
            channel_name=channel_name,
            channels_check=channels_check,
        )

        channel_checker = ingestion_validator.ChannelChecks(
            record_data,
            waveforms,
            images,
            internal_failed_channel,
        )

        """
            channel_dtype=["scalar", "missing", "scalar"]

            required_attributes = {
                "scalar": {"data": "missing"},
                "image": {"image_path": "missing", "path": "missing", "data": "missing"}
                "waveform": {
                    "waveform_id": "missing",
                    "id_": "missing",
                    "x": "missing",
                    "y": "missing"
                },
            }

            optional_attributes = {
                "scalar": {"units": "invalid"},
                "image": {
                    "exposure_time_s": "invalid",
                    "gain": "invalid",
                    "x_pixel_size": "invalid",
                    "x_pixel_units": "invalid",
                    "y_pixel_size": "invalid",
                    "y_pixel_units": "invalid",
                    "thumbnail": "invalid",
                },
                "waveform": {
                    "x_units": "invalid",
                    "y_units": "invalid",
                    "thumbnail": "invalid"
                },
            }

            unrecognised_attribute = {
                "scalar": ["dataset", "group"]
                "image": ["dataset", "group"]
                "waveform": ["dataset1", "dataset2", "group1", "group2"]
            }

            channel_name = [scalar, image, waveform]
        """

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
                    {
                        "N_COMP_FF_IMAGE": "x_pixel_size attribute has wrong datatype",
                    },
                    {
                        "N_COMP_FF_IMAGE": "x_pixel_units attribute has wrong datatype",
                    },
                    {
                        "N_COMP_FF_IMAGE": "data attribute has wrong datatype, "
                        "should be uint16 or uint8",
                    },
                ],
                id="Image required and optional attributes fail",
            ),
            pytest.param(
                "test3",
                [
                    {
                        "N_COMP_SPEC_TRACE": "y attribute must be a list of floats",
                    },
                    {
                        "N_COMP_SPEC_TRACE": "x_units attribute has wrong datatype",
                    },
                    {
                        "N_COMP_SPEC_TRACE": "y attribute has wrong shape",
                    },
                ],
                id="Waveform optional attributes and dataset fail",
            ),
            pytest.param(
                "test4",
                [
                    {
                        "N_COMP_FF_IMAGE": "unexpected group or dataset in "
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
        (
            record_data,
            waveforms,
            images,
            internal_failed_channel,
        ) = await create_test_hdf_file(test_type=test_type)

        channel_checker = ingestion_validator.ChannelChecks(
            record_data,
            waveforms,
            images,
            internal_failed_channel,
        )

        channel_response = create_channel_response(response)

        assert await channel_checker.channel_checks() == channel_response


class TestPartialImport:
    @pytest.mark.parametrize(
        "test_type, response",
        [
            pytest.param(
                "match",
                "accept record and merge",
                id="Metadata matches",
            ),
            pytest.param(
                "time",
                "timestamp matches, other metadata does not",
                id="Timestamp matches",
            ),
            pytest.param(
                "num",
                "shotnum matches, other metadata does not",
                id="Shotnum matches",
            ),
            pytest.param(
                "neither",
                "accept as a new record",
                id="Neither shotnum nor timestamp matches",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_metadata_checks(self, remove_hdf_file, test_type, response):

        (
            record_data,
            waveforms,
            images,
            internal_failed_channel,
        ) = await create_test_hdf_file()

        if test_type == "match":
            stored_record = copy.deepcopy(record_data)

        if test_type == "time":
            stored_record = copy.deepcopy(record_data)
            # alter so only time matches
            stored_record.metadata.epac_ops_data_version = "2.3"
            stored_record.metadata.shotnum = 234
            stored_record.metadata.active_area = "ae2"
            stored_record.metadata.active_experiment = "4898"

        if test_type == "num":
            stored_record = copy.deepcopy(record_data)
            # alter so only num matches
            stored_record.metadata.epac_ops_data_version = "2.3"
            stored_record.metadata.timestamp = "3122-04-07 14:28:16"
            stored_record.metadata.active_area = "ae2"
            stored_record.metadata.active_experiment = "4898"

        if test_type == "neither":
            stored_record = copy.deepcopy(record_data)
            # alter so neither shotnum nor timestamp matches
            stored_record.metadata.timestamp = "3122-04-07 14:28:16"
            stored_record.metadata.shotnum = 234

        partial_import_checker = ingestion_validator.PartialImportChecks(
            record_data,
            stored_record,
        )

        if test_type == "match" or test_type == "neither":
            assert partial_import_checker.metadata_checks() == response
        else:
            with pytest.raises(RejectRecordError, match=response):
                partial_import_checker.metadata_checks()

    @pytest.mark.parametrize(
        "test_type, response",
        [
            pytest.param(
                "all",
                {
                    "accepted channels": [],
                    "rejected channels": {
                        "GEM_SHOT_NUM_VALUE": "Channel is already present in "
                        "existing record",
                        "GEM_SHOT_SOURCE_STRING": "Channel is already present "
                        "in existing record",
                        "GEM_SHOT_TYPE_STRING": "Channel is already present in "
                        "existing record",
                        "GEM_WP_POS_VALUE": "Channel is already present in "
                        "existing record",
                        "N_COMP_CALCULATEDE_VALUE": "Channel is already present "
                        "in existing record",
                        "N_COMP_FF_E": "Channel is already present in existing record",
                        "N_COMP_FF_IMAGE": "Channel is already present in existing "
                        "record",
                        "N_COMP_FF_INTEGRATION": "Channel is already present in "
                        "existing record",
                        "N_COMP_FF_XPOS": "Channel is already present in existing "
                        "record",
                        "N_COMP_FF_YPOS": "Channel is already present in existing "
                        "record",
                        "N_COMP_NF_IMAGE": "Channel is already present in existing "
                        "record",
                        "N_COMP_SPEC_TRACE": "Channel is already present in "
                        "existing record",
                        "N_COMP_THROUGHPUTE_VALUE": "Channel is already present in "
                        "existing record",
                        "TA3_SHOT_NUM_VALUE": "Channel is already present in "
                        "existing record",
                        "Type": "Channel is already present in existing record",
                    },
                },
                id="All channels match",
            ),
            pytest.param(
                "some",
                {
                    "accepted channels": [
                        "GEM_SHOT_NUM_VALUE",
                        "N_COMP_FF_YPOS",
                        "Type",
                    ],
                    "rejected channels": {
                        "GEM_SHOT_SOURCE_STRING": "Channel is already present in "
                        "existing record",
                        "GEM_SHOT_TYPE_STRING": "Channel is already present in "
                        "existing record",
                        "GEM_WP_POS_VALUE": "Channel is already present in existing "
                        "record",
                        "N_COMP_CALCULATEDE_VALUE": "Channel is already present in "
                        "existing record",
                        "N_COMP_FF_E": "Channel is already present in existing record",
                        "N_COMP_FF_IMAGE": "Channel is already present in existing "
                        "record",
                        "N_COMP_FF_INTEGRATION": "Channel is already present in "
                        "existing record",
                        "N_COMP_FF_XPOS": "Channel is already present in existing "
                        "record",
                        "N_COMP_NF_IMAGE": "Channel is already present in existing "
                        "record",
                        "N_COMP_SPEC_TRACE": "Channel is already present in "
                        "existing record",
                        "N_COMP_THROUGHPUTE_VALUE": "Channel is already present in "
                        "existing record",
                        "TA3_SHOT_NUM_VALUE": "Channel is already present in existing "
                        "record",
                    },
                },
                id="Some channels match",
            ),
            pytest.param(
                "none",
                {
                    "accepted channels": [
                        "GEM_SHOT_NUM_VALUE",
                        "GEM_SHOT_SOURCE_STRING",
                        "GEM_SHOT_TYPE_STRING",
                        "GEM_WP_POS_VALUE",
                        "N_COMP_CALCULATEDE_VALUE",
                        "N_COMP_FF_E",
                        "N_COMP_FF_IMAGE",
                        "N_COMP_FF_INTEGRATION",
                        "N_COMP_FF_XPOS",
                        "N_COMP_FF_YPOS",
                        "N_COMP_NF_IMAGE",
                        "N_COMP_SPEC_TRACE",
                        "N_COMP_THROUGHPUTE_VALUE",
                        "TA3_SHOT_NUM_VALUE",
                        "Type",
                    ],
                    "rejected channels": {},
                },
                id="No channels match",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_import_channel_checks(self, remove_hdf_file, test_type, response):

        (
            record_data,
            waveforms,
            images,
            internal_failed_channel,
        ) = await create_test_hdf_file()

        if test_type == "all":
            stored_record = copy.deepcopy(record_data)

        if test_type == "some":
            stored_record = copy.deepcopy(record_data)
            channels = stored_record.channels
            # alter so only some match
            channels["GEM"] = channels.pop("GEM_SHOT_NUM_VALUE")
            channels["COMP"] = channels.pop("N_COMP_FF_YPOS")
            channels["TYP"] = channels.pop("Type")

        if test_type == "none":
            stored_record = copy.deepcopy(record_data)
            channels = stored_record.channels
            # alter so all match
            channels["a"] = channels.pop("GEM_SHOT_NUM_VALUE")
            channels["b"] = channels.pop("GEM_SHOT_SOURCE_STRING")
            channels["c"] = channels.pop("GEM_SHOT_TYPE_STRING")
            channels["d"] = channels.pop("GEM_WP_POS_VALUE")
            channels["e"] = channels.pop("N_COMP_CALCULATEDE_VALUE")
            channels["f"] = channels.pop("N_COMP_FF_E")
            channels["g"] = channels.pop("N_COMP_FF_IMAGE")
            channels["h"] = channels.pop("N_COMP_FF_INTEGRATION")
            channels["i"] = channels.pop("N_COMP_FF_XPOS")
            channels["j"] = channels.pop("N_COMP_FF_YPOS")
            channels["k"] = channels.pop("N_COMP_NF_IMAGE")
            channels["l"] = channels.pop("N_COMP_SPEC_TRACE")
            channels["m"] = channels.pop("N_COMP_THROUGHPUTE_VALUE")
            channels["n"] = channels.pop("TA3_SHOT_NUM_VALUE")
            channels["o"] = channels.pop("Type")

        partial_import_checker = ingestion_validator.PartialImportChecks(
            record_data,
            stored_record,
        )

        assert partial_import_checker.channel_checks() == response
