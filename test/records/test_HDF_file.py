import copy

from fastapi.testclient import TestClient
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
        pm_201_fe_cam_1 = record.create_group("PM-201-FE-CAM-1")
        pm_201_fe_cam_1.attrs.create("channel_dtype", "image")
        pm_201_fe_cam_1.attrs.create("exposure_time_s", 0.001)
        pm_201_fe_cam_1.attrs.create("gain", 5.5)
        pm_201_fe_cam_1.attrs.create("x_pixel_size", "441")
        pm_201_fe_cam_1.attrs.create("x_pixel_units", 42)
        pm_201_fe_cam_1.attrs.create("y_pixel_size", 441.0)
        pm_201_fe_cam_1.attrs.create("y_pixel_units", "µm")
        # example 2D dataset
        data = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]], dtype=np.uint32)
        pm_201_fe_cam_1.create_dataset("data", data=data)

    if test_type == "test3":
        pm_201_hj_pd = record.create_group("PM-201-HJ-PD")
        pm_201_hj_pd.attrs.create("channel_dtype", "waveform")
        pm_201_hj_pd.attrs.create("x_units", 23)
        pm_201_hj_pd.attrs.create("y_units", "kJ")
        x = [1, 2, 3, 4, 5, 6]
        pm_201_hj_pd.create_dataset("x", data=x)
        pm_201_hj_pd.create_dataset("y", data=6)

    if test_type == "test4":
        pm_201_fe_cam_1 = record.create_group("PM-201-FE-CAM-1")
        pm_201_fe_cam_1.create_group("unrecognised_group")
        pm_201_fe_cam_1.attrs.create("channel_dtype", "image")
        pm_201_fe_cam_1.attrs.create("exposure_time_s", 0.001)
        pm_201_fe_cam_1.attrs.create("gain", 5.5)
        pm_201_fe_cam_1.attrs.create("x_pixel_size", "441.0")
        pm_201_fe_cam_1.attrs.create("x_pixel_units", 456)
        pm_201_fe_cam_1.attrs.create("y_pixel_size", 441.0)
        pm_201_fe_cam_1.attrs.create("y_pixel_units", "µm")
        pm_201_fe_cam_1.create_dataset("unrecognised_dataset", data=4)


async def create_test_hdf_file(  # noqa: C901
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

        pm_201_fe_en = record.create_group("PM-201-FE-EM")
        pm_201_fe_en.attrs.create("channel_dtype", "scalar")
        if required_attributes and "scalar" in required_attributes:
            scalar = required_attributes["scalar"]
            if scalar["data"] != "missing":
                pm_201_fe_en.create_dataset("data", data=(scalar["data"]))
        else:
            pm_201_fe_en.create_dataset("data", data=366272)

        pm_201_fe_cam_2_cenx = record.create_group("PM-201-FE-CAM-2-CENX")
        if scalar_1_channel_dtype is not None:
            if scalar_1_channel_dtype[1] == "exists":
                pm_201_fe_cam_2_cenx.attrs.create(
                    "channel_dtype",
                    scalar_1_channel_dtype[0],
                )
        else:
            pm_201_fe_cam_2_cenx.attrs.create("channel_dtype", "scalar")
        pm_201_fe_cam_2_cenx.create_dataset("data", data="EX")

        pm_201_fe_cam_2_fwhmx = record.create_group("PM-201-FE-CAM-2-FWHMX")
        if scalar_2_channel_dtype is not None:
            if scalar_2_channel_dtype[1] == "exists":
                pm_201_fe_cam_2_fwhmx.attrs.create(
                    "channel_dtype",
                    scalar_2_channel_dtype[0],
                )
        else:
            pm_201_fe_cam_2_fwhmx.attrs.create("channel_dtype", "scalar")
        pm_201_fe_cam_2_fwhmx.create_dataset("data", data="FP")

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

        pm_201_fe_cam_2 = record.create_group("PM-201-FE-CAM-2")
        pm_201_fe_cam_2.attrs.create("channel_dtype", "image")
        pm_201_fe_cam_2.attrs.create("exposure_time_s", 0.001)
        pm_201_fe_cam_2.attrs.create("gain", 5.5)
        pm_201_fe_cam_2.attrs.create("x_pixel_size", 441.0)
        pm_201_fe_cam_2.attrs.create("x_pixel_units", "µm")
        pm_201_fe_cam_2.attrs.create("y_pixel_size", 441.0)
        pm_201_fe_cam_2.attrs.create("y_pixel_units", "µm")
        data = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]], dtype=np.uint16)
        pm_201_fe_cam_2.create_dataset("data", data=data)

        pm_201_fe_cam_2_ceny = record.create_group("PM-201-FE-CAM-2-CENY")
        if (
            unrecognised_attribute
            and "scalar" in unrecognised_attribute
            and "group" in unrecognised_attribute["scalar"]
        ):
            pm_201_fe_cam_2_ceny.create_group("unrecognised_group")
        pm_201_fe_cam_2_ceny.attrs.create("channel_dtype", "scalar")
        pm_201_fe_cam_2_ceny.attrs.create("units", "ms")
        if (
            unrecognised_attribute
            and "scalar" in unrecognised_attribute
            and "dataset" in unrecognised_attribute["scalar"]
        ):
            pm_201_fe_cam_2_ceny.create_dataset("unrecognised_dataset", data=35)
        pm_201_fe_cam_2_ceny.create_dataset("data", data=45)

        pm_201_fe_cam_2_fwhmy = record.create_group("PM-201-FE-CAM-2-FWHMY")
        pm_201_fe_cam_2_fwhmy.attrs.create("channel_dtype", "scalar")
        pm_201_fe_cam_2_fwhmy.attrs.create("units", "mm")
        pm_201_fe_cam_2_fwhmy.create_dataset("data", data=10.84)

        pm_201_pa1_em = record.create_group("PM-201-PA1-EM")
        pm_201_pa1_em.attrs.create("channel_dtype", "scalar")
        pm_201_pa1_em.attrs.create("units", "mg")
        pm_201_pa1_em.create_dataset("data", data=-8895000.0)

        if test_type != "test2" and test_type != "test4":
            pm_201_fe_cam_1 = record.create_group("PM-201-FE-CAM-1")
            if (
                unrecognised_attribute
                and "image" in unrecognised_attribute
                and "group" in unrecognised_attribute["image"]
            ):
                pm_201_fe_cam_1.create_group("unrecognised_group")
            if image_channel_dtype is not None:
                if image_channel_dtype[1] == "exists":
                    pm_201_fe_cam_1.attrs.create(
                        "channel_dtype",
                        image_channel_dtype[0],
                    )
            else:
                pm_201_fe_cam_1.attrs.create("channel_dtype", "image")
            if optional_attributes and "image" in optional_attributes:
                image = optional_attributes["image"]
                if "exposure_time_s" in image:
                    if image["exposure_time_s"] == "invalid":
                        pm_201_fe_cam_1.attrs.create("exposure_time_s", "0.001")
                else:
                    pm_201_fe_cam_1.attrs.create("exposure_time_s", 0.001)
                if "gain" in image:
                    if image["gain"] == "invalid":
                        pm_201_fe_cam_1.attrs.create("gain", "5.5")
                else:
                    pm_201_fe_cam_1.attrs.create("gain", 5.5)
                if "x_pixel_size" in image:
                    if image["x_pixel_size"] == "invalid":
                        pm_201_fe_cam_1.attrs.create("x_pixel_size", "441.0")
                else:
                    pm_201_fe_cam_1.attrs.create("x_pixel_size", 441.0)
                if "x_pixel_units" in image:
                    if image["x_pixel_units"] == "invalid":
                        pm_201_fe_cam_1.attrs.create("x_pixel_units", 436)
                else:
                    pm_201_fe_cam_1.attrs.create("x_pixel_units", "µm")
                if "y_pixel_size" in image:
                    if image["y_pixel_size"] == "invalid":
                        pm_201_fe_cam_1.attrs.create("y_pixel_size", "441.0")
                else:
                    pm_201_fe_cam_1.attrs.create("y_pixel_size", 441.0)
                if "y_pixel_units" in image:
                    if image["y_pixel_units"] == "invalid":
                        pm_201_fe_cam_1.attrs.create("y_pixel_units", 346)
                else:
                    pm_201_fe_cam_1.attrs.create("y_pixel_units", "µm")
            else:
                pm_201_fe_cam_1.attrs.create("exposure_time_s", 0.001)
                pm_201_fe_cam_1.attrs.create("gain", 5.5)
                pm_201_fe_cam_1.attrs.create("x_pixel_size", 441.0)
                pm_201_fe_cam_1.attrs.create("x_pixel_units", "µm")
                pm_201_fe_cam_1.attrs.create("y_pixel_size", 441.0)
                pm_201_fe_cam_1.attrs.create("y_pixel_units", "µm")
            # example 2D dataset
            if (
                unrecognised_attribute
                and "image" in unrecognised_attribute
                and "dataset" in unrecognised_attribute["image"]
            ):
                pm_201_fe_cam_1.create_dataset("unrecognised_dataset", data=35)
            data = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]], dtype=np.uint16)
            if required_attributes and "image" in required_attributes:
                image = required_attributes["image"]
                if image["data"] != "missing":
                    pm_201_fe_cam_1.create_dataset("data", data=(image["data"]))
            else:
                pm_201_fe_cam_1.create_dataset("data", data=data)

        pm_201_pa2_em = record.create_group("PM-201-PA2-EM")
        pm_201_pa2_em.attrs.create("channel_dtype", "scalar")
        if optional_attributes and "scalar" in optional_attributes:
            scalar = optional_attributes["scalar"]
            if scalar["units"] == "invalid":
                pm_201_pa2_em.attrs.create("units", 764)
            else:
                pm_201_pa2_em.attrs.create("units", "µm")
        else:
            pm_201_pa2_em.attrs.create("units", "µm")
        pm_201_pa2_em.create_dataset("data", data=8895000.0)

        pm_201_tj_em = record.create_group("PM-201-TJ-EM")
        pm_201_tj_em.attrs.create("channel_dtype", "scalar")
        pm_201_tj_em.attrs.create("units", "mm")
        pm_201_tj_em.create_dataset("data", data=330.523)

        if channels_check:
            pm_201_tj_cam_2_cenx = record.create_group("ALL_FALSE_SCALAR")
            pm_201_tj_cam_2_cenx.attrs.create("channel_dtype", "thing")
            pm_201_tj_cam_2_cenx.attrs.create("units", 44)
            pm_201_tj_cam_2_cenx.create_dataset("data", data=["data"])
            pm_201_tj_cam_2_cenx.create_dataset(
                "unrecognised_scalar_dataset",
                data=[32],
            )
        else:
            pm_201_tj_cam_2_cenx = record.create_group("PM-201-TJ-CAM-2-CENX")
            pm_201_tj_cam_2_cenx.attrs.create("channel_dtype", "scalar")
            pm_201_tj_cam_2_cenx.attrs.create("units", "mm")
            pm_201_tj_cam_2_cenx.create_dataset("data", data=243.771)

        pm_201_tj_cam_2_fwhmx = record.create_group("PM-201-TJ-CAM-2-FWHMX")
        pm_201_tj_cam_2_fwhmx.attrs.create("channel_dtype", "scalar")
        pm_201_tj_cam_2_fwhmx.attrs.create("units", "cm")
        pm_201_tj_cam_2_fwhmx.create_dataset("data", data=74)

        pm_201_tj_cam_2_ceny = record.create_group("PM-201-TJ-CAM-2-CENY")
        pm_201_tj_cam_2_ceny.attrs.create("channel_dtype", "scalar")
        pm_201_tj_cam_2_ceny.create_dataset("data", data=217343.0)

        if test_type != "test3":
            pm_201_hj_pd = record.create_group("PM-201-HJ-PD")
            if (
                unrecognised_attribute
                and "waveform" in unrecognised_attribute
                and "group1" in unrecognised_attribute["waveform"]
            ):
                pm_201_hj_pd.create_group("unrecognised_group1")
            if (
                unrecognised_attribute
                and "waveform" in unrecognised_attribute
                and "group2" in unrecognised_attribute["waveform"]
            ):
                pm_201_hj_pd.create_group("unrecognised_group2")
            if waveform_channel_dtype is not None:
                if waveform_channel_dtype[1] == "exists":
                    pm_201_hj_pd.attrs.create(
                        "channel_dtype",
                        waveform_channel_dtype[0],
                    )
            else:
                pm_201_hj_pd.attrs.create("channel_dtype", "waveform")
            if optional_attributes and "waveform" in optional_attributes:
                waveform = optional_attributes["waveform"]
                if "x_units" in waveform:
                    if waveform["x_units"] == "invalid":
                        pm_201_hj_pd.attrs.create("x_units", 35)
                else:
                    pm_201_hj_pd.attrs.create("x_units", "s")
                if "y_units" in waveform:
                    if waveform["y_units"] == "invalid":
                        pm_201_hj_pd.attrs.create("y_units", 42)
                else:
                    pm_201_hj_pd.attrs.create("y_units", "kJ")
            else:
                pm_201_hj_pd.attrs.create("x_units", "s")
                pm_201_hj_pd.attrs.create("y_units", "kJ")
            x = [1, 2, 3, 4, 5, 6]
            y = [8, 3, 6, 2, 3, 8, 425]
            if required_attributes and "waveform" in required_attributes:
                waveform = required_attributes["waveform"]
                if "x" in waveform:
                    if waveform["x"] != "missing":
                        pm_201_hj_pd.create_dataset("x", data=(waveform["x"]))
                else:
                    pm_201_hj_pd.create_dataset("x", data=x)
                if "y" in waveform:
                    if waveform["y"] != "missing":
                        pm_201_hj_pd.create_dataset("y", data=(waveform["y"]))
                else:
                    pm_201_hj_pd.create_dataset("y", data=y)
            else:
                pm_201_hj_pd.create_dataset("x", data=x)
                pm_201_hj_pd.create_dataset("y", data=y)
            if (
                unrecognised_attribute
                and "waveform" in unrecognised_attribute
                and "dataset1" in unrecognised_attribute["waveform"]
            ):
                pm_201_hj_pd.create_dataset("unrecognised_dataset1", data=35)
            if (
                unrecognised_attribute
                and "waveform" in unrecognised_attribute
                and "dataset2" in unrecognised_attribute["waveform"]
            ):
                pm_201_hj_pd.create_dataset("unrecognised_dataset2", data=35)

        pm_201_tj_cam_2_fwhmy = record.create_group("PM-201-TJ-CAM-2-FWHMY")
        pm_201_tj_cam_2_fwhmy.attrs.create("channel_dtype", "scalar")
        pm_201_tj_cam_2_fwhmy.create_dataset("data", data="GS")

    hdf_handler = HDFDataHandler(hdf_file_path)
    return await hdf_handler.extract_data()


def create_channel_response(responses, extra=None, channels=False):
    model_response = {
        "accepted channels": [
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
        "rejected channels": {},
    }

    if extra:
        responses = extra

    if channels:
        model_response["accepted channels"].remove("PM-201-TJ-CAM-2-CENX")

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
            "rejected channels": {},
        }

    @pytest.mark.parametrize(
        "altered_channel, response",
        [
            pytest.param(
                ["scalar", "missing", "scalar"],
                [
                    {
                        "PM-201-FE-CAM-2-CENX": "channel_dtype attribute is "
                        "missing (cannot perform other checks without)",
                    },
                ],
                id="Scalar channel_dtype missing",
            ),
            pytest.param(
                ["image", "missing", "image"],
                [
                    {
                        "PM-201-FE-CAM-1": "channel_dtype attribute is missing "
                        "(cannot perform other checks without)",
                    },
                ],
                id="Image channel_dtype missing",
            ),
            pytest.param(
                ["waveform", "missing", "waveform"],
                [
                    {
                        "PM-201-HJ-PD": "channel_dtype attribute is missing "
                        "(cannot perform other checks without)",
                    },
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
                    {
                        "PM-201-FE-CAM-1": "channel_dtype attribute is missing "
                        "(cannot perform other checks without)",
                    },
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
            },
            "waveform": {
                "x_units": "invalid",
                "y_units": "invalid",
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
                    {
                        "PM-201-FE-CAM-2-CENX": "channel_dtype attribute is missing "
                        "(cannot perform other checks without)",
                    },
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
                },
                "waveform": {
                    "x_units": "invalid",
                    "y_units": "invalid",
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
                        "PM-201-FE-CAM-1": "x_pixel_size attribute has wrong datatype",
                    },
                    {
                        "PM-201-FE-CAM-1": "x_pixel_units attribute has wrong datatype",
                    },
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
                        "PM-201-FE-EM": "Channel is already present in "
                        "existing record",
                        "PM-201-FE-CAM-2-CENX": "Channel is already present "
                        "in existing record",
                        "PM-201-FE-CAM-2-FWHMX": "Channel is already present in "
                        "existing record",
                        "PM-201-FE-CAM-2-CENY": "Channel is already present in "
                        "existing record",
                        "PM-201-FE-CAM-2-FWHMY": "Channel is already present "
                        "in existing record",
                        "PM-201-PA1-EM": "Channel is already present in existing "
                        "record",
                        "PM-201-FE-CAM-1": "Channel is already present in existing "
                        "record",
                        "PM-201-PA2-EM": "Channel is already present in "
                        "existing record",
                        "PM-201-TJ-EM": "Channel is already present in existing "
                        "record",
                        "PM-201-TJ-CAM-2-CENX": "Channel is already present in "
                        "existing record",
                        "PM-201-FE-CAM-2": "Channel is already present in existing "
                        "record",
                        "PM-201-HJ-PD": "Channel is already present in "
                        "existing record",
                        "PM-201-TJ-CAM-2-FWHMX": "Channel is already present in "
                        "existing record",
                        "PM-201-TJ-CAM-2-CENY": "Channel is already present in "
                        "existing record",
                        "PM-201-TJ-CAM-2-FWHMY": "Channel is already present in "
                        "existing record",
                    },
                },
                id="All channels match",
            ),
            pytest.param(
                "some",
                {
                    "accepted channels": [
                        "PM-201-FE-EM",
                        "PM-201-TJ-CAM-2-CENX",
                        "PM-201-TJ-CAM-2-FWHMY",
                    ],
                    "rejected channels": {
                        "PM-201-FE-CAM-2-CENX": "Channel is already present in "
                        "existing record",
                        "PM-201-FE-CAM-2-FWHMX": "Channel is already present in "
                        "existing record",
                        "PM-201-FE-CAM-2-CENY": "Channel is already present in "
                        "existing record",
                        "PM-201-FE-CAM-2-FWHMY": "Channel is already present in "
                        "existing record",
                        "PM-201-PA1-EM": "Channel is already present in existing "
                        "record",
                        "PM-201-FE-CAM-1": "Channel is already present in existing "
                        "record",
                        "PM-201-PA2-EM": "Channel is already present in "
                        "existing record",
                        "PM-201-TJ-EM": "Channel is already present in existing "
                        "record",
                        "PM-201-FE-CAM-2": "Channel is already present in existing "
                        "record",
                        "PM-201-HJ-PD": "Channel is already present in "
                        "existing record",
                        "PM-201-TJ-CAM-2-FWHMX": "Channel is already present in "
                        "existing record",
                        "PM-201-TJ-CAM-2-CENY": "Channel is already present in "
                        "existing record",
                    },
                },
                id="Some channels match",
            ),
            pytest.param(
                "none",
                {
                    "accepted channels": [
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
            channels["GEM"] = channels.pop("PM-201-FE-EM")
            channels["COMP"] = channels.pop("PM-201-TJ-CAM-2-CENX")
            channels["TYP"] = channels.pop("PM-201-TJ-CAM-2-FWHMY")

        if test_type == "none":
            stored_record = copy.deepcopy(record_data)
            channels = stored_record.channels
            # alter so all match
            channels["a"] = channels.pop("PM-201-FE-EM")
            channels["b"] = channels.pop("PM-201-FE-CAM-2-CENX")
            channels["c"] = channels.pop("PM-201-FE-CAM-2-FWHMX")
            channels["d"] = channels.pop("PM-201-FE-CAM-2-CENY")
            channels["e"] = channels.pop("PM-201-FE-CAM-2-FWHMY")
            channels["f"] = channels.pop("PM-201-PA1-EM")
            channels["g"] = channels.pop("PM-201-FE-CAM-1")
            channels["h"] = channels.pop("PM-201-PA2-EM")
            channels["i"] = channels.pop("PM-201-TJ-EM")
            channels["j"] = channels.pop("PM-201-TJ-CAM-2-CENX")
            channels["k"] = channels.pop("PM-201-FE-CAM-2")
            channels["l"] = channels.pop("PM-201-HJ-PD")
            channels["m"] = channels.pop("PM-201-TJ-CAM-2-FWHMX")
            channels["n"] = channels.pop("PM-201-TJ-CAM-2-CENY")
            channels["o"] = channels.pop("PM-201-TJ-CAM-2-FWHMY")

        partial_import_checker = ingestion_validator.PartialImportChecks(
            record_data,
            stored_record,
        )

        assert partial_import_checker.channel_checks() == response


class TestIntegrationIngestData:
    @pytest.mark.parametrize(
        "test_type, response",
        [
            pytest.param(
                "match",
                "accept record and merge",
                id="Metadata matches",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_ingest_data(
        self,
        remove_hdf_file,
        test_app: TestClient,
        test_type,
        response,
    ):

        (
            record_data,
            waveforms,
            images,
            internal_failed_channel,
        ) = await create_test_hdf_file()
        stored_record = None

        if stored_record:
            partial_import_checker = ingestion_validator.PartialImportChecks(
                record_data,
                stored_record,
            )
            accept_type = partial_import_checker.metadata_checks()
            channel_list = partial_import_checker.channel_checks()

            # TODO do something here about merging stored and incoming

        file_checker = ingestion_validator.FileChecks(record_data)
        warning = file_checker.epac_data_version_checks()

        print(warning)

        record_checker = ingestion_validator.RecordChecks(record_data)
        record_checker.active_area_checks()
        record_checker.optional_metadata_checks()

        channel_checker = ingestion_validator.ChannelChecks(
            record_data,
            waveforms,
            images,
            internal_failed_channel,
        )
        channel_list = await channel_checker.channel_checks()

        # test_response = test_app.get(
        #    f"/records/{record_id}?truncate={json.dumps(truncate)}",
        #    headers={"Authorization": f"Bearer {login_and_get_token}"},
        # )
