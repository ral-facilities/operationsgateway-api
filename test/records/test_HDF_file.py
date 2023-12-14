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


def create_test_hdf_file(
    data_version=None,
    timestamp=None,
    active_area=None,
    shotnum=None,
    active_experiment=None,
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

        gem_shot_num_value = record.create_group("GEM_SHOT_NUM_VALUE")
        gem_shot_num_value.attrs.create("channel_dtype", "scalar")
        gem_shot_num_value.create_dataset("data", data=366272)

        gem_shot_source_string = record.create_group("GEM_SHOT_SOURCE_STRING")
        gem_shot_source_string.attrs.create("channel_dtype", "scalar")
        gem_shot_source_string.create_dataset("data", data="EX")

        gem_shot_type_string = record.create_group("GEM_SHOT_TYPE_STRING")
        gem_shot_type_string.attrs.create("channel_dtype", "scalar")
        gem_shot_type_string.create_dataset("data", data="FP")

        gem_wp_pos_value = record.create_group("GEM_WP_POS_VALUE")
        gem_wp_pos_value.attrs.create("channel_dtype", "scalar")
        gem_wp_pos_value.attrs.create("units", "ms")
        gem_wp_pos_value.create_dataset("data", data=45)

        n_comp_calculatede_value = record.create_group("N_COMP_CALCULATEDE_VALUE")
        n_comp_calculatede_value.attrs.create("channel_dtype", "scalar")
        n_comp_calculatede_value.attrs.create("units", "mm")
        n_comp_calculatede_value.create_dataset("data", data=10.84)

        n_comp_ff_e = record.create_group("N_COMP_FF_E")
        n_comp_ff_e.attrs.create("channel_dtype", "scalar")
        n_comp_ff_e.attrs.create("units", "mg")
        n_comp_ff_e.create_dataset("data", data=-8895000.0)

        n_comp_ff_image = record.create_group("N_COMP_FF_IMAGE")
        n_comp_ff_image.attrs.create("channel_dtype", "image")
        n_comp_ff_image.attrs.create("exposure_time_s", 0.001)
        n_comp_ff_image.attrs.create("gain", 5.5)
        n_comp_ff_image.attrs.create("x_pixel_size", 441.0)
        n_comp_ff_image.attrs.create("x_pixel_units", "µm")
        n_comp_ff_image.attrs.create("y_pixel_size", 441.0)
        n_comp_ff_image.attrs.create("y_pixel_units", "µm")
        # example 2D dataset
        data = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]], dtype=np.uint16)
        n_comp_ff_image.create_dataset("data", data=data)

        n_comp_ff_intergration = record.create_group("N_COMP_FF_INTEGRATION")
        n_comp_ff_intergration.attrs.create("channel_dtype", "scalar")
        n_comp_ff_intergration.attrs.create("units", "µm")
        n_comp_ff_intergration.create_dataset("data", data=8895000.0)

        n_comp_ff_xpos = record.create_group("N_COMP_FF_XPOS")
        n_comp_ff_xpos.attrs.create("channel_dtype", "scalar")
        n_comp_ff_xpos.attrs.create("units", "mm")
        n_comp_ff_xpos.create_dataset("data", data=330.523)

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

        n_comp_spec_trace = record.create_group("N_COMP_SPEC_TRACE")
        n_comp_spec_trace.attrs.create("channel_dtype", "waveform")
        n_comp_spec_trace.attrs.create("x_units", "s")
        n_comp_spec_trace.attrs.create("y_units", "kJ")
        x = [1, 2, 3, 4, 5, 6]
        y = [8, 3, 6, 2, 3, 8, 425]
        n_comp_spec_trace.create_dataset("x", data=x)
        n_comp_spec_trace.create_dataset("y", data=y)

        types = record.create_group("Type")
        types.attrs.create("channel_dtype", "scalar")
        types.create_dataset("data", data="GS")

    hdf_handler = HDFDataHandler(hdf_file_path)
    return hdf_handler.extract_data()


# poetry run pytest -s "test/records/test_HDF_file.py::TestFile" -v -vv
class TestFile:
    def test_file_checks_pass(self, remove_hdf_file):
        record_data, waveforms, images, _ = create_test_hdf_file()
        file_checker = ingestion_validator.FileChecks(record_data)

        file_checker.epac_data_version_checks()

    def test_minor_version_too_high(self, remove_hdf_file):
        record_data, waveforms, images, _ = create_test_hdf_file(
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
    def test_epac_ops_data_version_missing(self, data_version, match, remove_hdf_file):
        record_data, waveforms, images, _ = create_test_hdf_file(data_version=data_version)
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
    def test_record_checks_pass(self, shotnum, active_experiment, remove_hdf_file):
        record_data, waveforms, images, _ = create_test_hdf_file(
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
    def test_record_checks_fail(
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
                record_data, waveforms, images, _ = create_test_hdf_file(
                    active_area=active_area,
                    shotnum=shotnum,
                    active_experiment=active_experiment,
                )
        else:
            record_data, waveforms, images, _ = create_test_hdf_file(
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
        record_data, waveforms, images, channel_dtype_missing = create_test_hdf_file()
        
        channel_checker = ingestion_validator.ChannelChecks(
            record_data,
            waveforms,
            images,
            channel_dtype_missing,
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
                "N_COMP_SPEC_TRACE",
                "N_COMP_THROUGHPUTE_VALUE",
                "TA3_SHOT_NUM_VALUE",
                "Type",
            ],
            "rejected channels": {},
        }

    @pytest.mark.asyncio
    async def test_channel_dtype(self, remove_hdf_file):
        record_data, waveforms, images, channel_dtype_missing = create_test_hdf_file()
        channel_checker = ingestion_validator.ChannelChecks(
            record_data,
            waveforms,
            images,
            channel_dtype_missing,
        )

        dtype_response = await channel_checker.channel_dtype_checks()
        print(dtype_response)

    # attribute_response = channel_checker.required_attribute_checks()
    # optional_response = channel_checker.optional_dtype_checks()
    # dataset_response = channel_checker.dataset_checks()
    # unrecognised_response = channel_checker.unrecognised_attribute_checks()
    # channel_name_response = await channel_checker.channel_name_check()

    # response = await channel_checker.channel_checks()

    # print(attribute_response)
    # print(optional_response)
    # print(dataset_response)
    # print(unrecognised_response)
    # print(channel_name_response)
    # print(response)


class TestPartialImport:
    pass
