import asyncio
import pytest

import h5py
import numpy as np

from operationsgateway_api.src.exceptions import (
    RejectFileError,
    RejectRecordError,
    ModelError,
)
from operationsgateway_api.src.records import ingestion_validator
from operationsgateway_api.src.records.hdf_handler import HDFDataHandler


def create_test_hdf_file(
    data_version=["1.0", "exists"],
    timestamp=["2022-04-07 14:28:16", "exists"],
    active_area=["ea1", "exists"],
    shotnum=["valid", "exists"],
    active_experiment=["90097341", "exists"],
):

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

        GEM_SHOT_NUM_VALUE = record.create_group("GEM_SHOT_NUM_VALUE")
        GEM_SHOT_NUM_VALUE.attrs.create("channel_dtype", "scalar")
        GEM_SHOT_NUM_VALUE.create_dataset("data", data=366272)

        GEM_SHOT_SOURCE_STRING = record.create_group("GEM_SHOT_SOURCE_STRING")
        GEM_SHOT_SOURCE_STRING.attrs.create("channel_dtype", "scalar")
        GEM_SHOT_SOURCE_STRING.create_dataset("data", data="EX")

        GEM_SHOT_TYPE_STRING = record.create_group("GEM_SHOT_TYPE_STRING")
        GEM_SHOT_TYPE_STRING.attrs.create("channel_dtype", "scalar")
        GEM_SHOT_TYPE_STRING.create_dataset("data", data="FP")

        GEM_WP_POS_VALUE = record.create_group("GEM_WP_POS_VALUE")
        GEM_WP_POS_VALUE.attrs.create("channel_dtype", "scalar")
        GEM_WP_POS_VALUE.attrs.create("units", "ms")
        GEM_WP_POS_VALUE.create_dataset("data", data=45)

        N_COMP_CALCULATEDE_VALUE = record.create_group("N_COMP_CALCULATEDE_VALUE")
        N_COMP_CALCULATEDE_VALUE.attrs.create("channel_dtype", "scalar")
        N_COMP_CALCULATEDE_VALUE.attrs.create("units", "mm")
        N_COMP_CALCULATEDE_VALUE.create_dataset("data", data=10.84)

        N_COMP_FF_E = record.create_group("N_COMP_FF_E")
        N_COMP_FF_E.attrs.create("channel_dtype", "scalar")
        N_COMP_FF_E.attrs.create("units", "mg")
        N_COMP_FF_E.create_dataset("data", data=-8895000.0)

        N_COMP_FF_IMAGE = record.create_group("N_COMP_FF_IMAGE")
        N_COMP_FF_IMAGE.attrs.create("channel_dtype", "image")
        N_COMP_FF_IMAGE.attrs.create("exposure_time_s", 0.001)
        N_COMP_FF_IMAGE.attrs.create("gain", 5.5)
        N_COMP_FF_IMAGE.attrs.create("x_pixel_size", 441.0)
        N_COMP_FF_IMAGE.attrs.create("x_pixel_units", "µm")
        N_COMP_FF_IMAGE.attrs.create("y_pixel_size", 441.0)
        N_COMP_FF_IMAGE.attrs.create("y_pixel_units", "µm")
        # example 2D dataset
        data = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]], dtype=np.uint16)
        N_COMP_FF_IMAGE.create_dataset("data", data=data)

        N_COMP_FF_INTEGRATION = record.create_group("N_COMP_FF_INTEGRATION")
        N_COMP_FF_INTEGRATION.attrs.create("channel_dtype", "scalar")
        N_COMP_FF_INTEGRATION.attrs.create("units", "µm")
        N_COMP_FF_INTEGRATION.create_dataset("data", data=8895000.0)

        N_COMP_FF_XPOS = record.create_group("N_COMP_FF_XPOS")
        N_COMP_FF_XPOS.attrs.create("channel_dtype", "scalar")
        N_COMP_FF_XPOS.attrs.create("units", "mm")
        N_COMP_FF_XPOS.create_dataset("data", data=330.523)

        N_COMP_FF_YPOS = record.create_group("N_COMP_FF_YPOS")
        N_COMP_FF_YPOS.attrs.create("channel_dtype", "scalar")
        N_COMP_FF_YPOS.attrs.create("units", "mm")
        N_COMP_FF_YPOS.create_dataset("data", data=243.771)

        N_COMP_THROUGHPUTE_VALUE = record.create_group("N_COMP_THROUGHPUTE_VALUE")
        N_COMP_THROUGHPUTE_VALUE.attrs.create("channel_dtype", "scalar")
        N_COMP_THROUGHPUTE_VALUE.attrs.create("units", "cm")
        N_COMP_THROUGHPUTE_VALUE.create_dataset("data", data=74)

        TA3_SHOT_NUM_VALUE = record.create_group("TA3_SHOT_NUM_VALUE")
        TA3_SHOT_NUM_VALUE.attrs.create("channel_dtype", "scalar")
        TA3_SHOT_NUM_VALUE.create_dataset("data", data=217343.0)

        N_COMP_SPEC_TRACE = record.create_group("N_COMP_SPEC_TRACE")
        N_COMP_SPEC_TRACE.attrs.create("channel_dtype", "waveform")
        N_COMP_SPEC_TRACE.attrs.create("x_units", "s")
        N_COMP_SPEC_TRACE.attrs.create("y_units", "kJ")
        x = [1, 2, 3, 4, 5, 6]
        y = [8, 3, 6, 2, 3, 8, 425]
        N_COMP_SPEC_TRACE.create_dataset("x", data=x)
        N_COMP_SPEC_TRACE.create_dataset("y", data=y)

        Type = record.create_group("Type")
        Type.attrs.create("channel_dtype", "scalar")
        Type.create_dataset("data", data="GS")

    hdf_handler = HDFDataHandler(hdf_file_path)
    return hdf_handler.extract_data()


# poetry run pytest -s "test/records/test_HDF_file.py::TestFile" -v -vv
class TestFile:
    def test_file_checks_pass(self, remove_HDF_file):
        record_data, waveforms, images = create_test_hdf_file()
        file_checker = ingestion_validator.FileChecks(record_data)

        file_checker.epac_data_version_checks()

    def test_minor_version_too_high(self, remove_HDF_file):
        record_data, waveforms, images = create_test_hdf_file(
            data_version=["1.4", "exists"]
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
    def test_epac_ops_data_version_missing(self, data_version, match, remove_HDF_file):
        record_data, waveforms, images = create_test_hdf_file(data_version=data_version)
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
    def test_record_checks_pass(self, shotnum, active_experiment, remove_HDF_file):
        record_data, waveforms, images = create_test_hdf_file(
            shotnum=shotnum, active_experiment=active_experiment
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
        self, active_area, shotnum, active_experiment, test, match, remove_HDF_file
    ):
        if test == "other":
            with pytest.raises(ModelError):
                record_data, waveforms, images = create_test_hdf_file(
                    active_area=active_area,
                    shotnum=shotnum,
                    active_experiment=active_experiment,
                )
        else:
            record_data, waveforms, images = create_test_hdf_file(
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
    async def test_channel_dtype(self, remove_HDF_file):
        record_data, waveforms, images = create_test_hdf_file()
        channel_checker = ingestion_validator.ChannelChecks(
            record_data, waveforms, images
        )

        response = await channel_checker.channel_dtype_checks()
        print(response)


class TestPartialImport:
    pass
