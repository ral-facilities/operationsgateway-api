import h5py
import numpy as np

from operationsgateway_api.src.records.ingestion.hdf_handler import HDFDataHandler


def generate_channel_check_block(record, test_type):
    """
    Is ran inside the create_test_hdf_file to generate one of four tests
    depending on if that test was specified in any of the test functions
    """
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
    """
    Generates an HDF file and returns the output of hdf_handler.py
    the file can be changed depending on which values have been selected from the
    test functions
    """

    data_version = data_version if data_version is not None else ["1.0", "exists"]
    timestamp = (
        timestamp if timestamp is not None else ["2020-04-07 14:28:16", "exists"]
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
            data = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]], dtype=np.uint16)
            false_image.create_dataset("data", data=data)

        if channel_name and "waveform" in channel_name:
            false_waveform = record.create_group("FALSE_WAVEFORM")
            false_waveform.attrs.create("channel_dtype", "waveform")
            false_waveform.attrs.create("x_units", "s")
            false_waveform.attrs.create("y_units", "kJ")
            x = [1, 2, 3, 4, 5, 5456]
            y = [8, 3, 6, 2, 3, 8]
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
            y = [8, 3, 6, 2, 3, 8]
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
