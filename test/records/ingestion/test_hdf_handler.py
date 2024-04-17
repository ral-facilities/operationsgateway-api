import h5py
import numpy as np
import pytest

from operationsgateway_api.src.exceptions import HDFDataExtractionError
from operationsgateway_api.src.records.ingestion.hdf_handler import HDFDataHandler


def create_test_hdf_file(timestamp_test=False, data_test=False):
    with h5py.File("test.h5", "w") as f:
        f.attrs.create("epac_ops_data_version", "1.0")

        record = f["/"]
        if timestamp_test:
            record.attrs.create("timestamp", "20t0-04 07 a4 mh 228:1")
        else:
            record.attrs.create("timestamp", "2020-04-07 14:28:16")
        record.attrs.create("shotnum", 366272, dtype="u8")
        record.attrs.create("active_area", "ea1")
        record.attrs.create("active_experiment", "90097341")

        pm_201_fe_en = record.create_group("PM-201-FE-EM")
        pm_201_fe_en.attrs.create("channel_dtype", "scalar")
        if data_test:
            pm_201_fe_en.create_dataset("data", data=[366272])
        else:
            pm_201_fe_en.create_dataset("data", data=366272)

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

        pm_201_hj_pd = record.create_group("PM-201-HJ-PD")
        pm_201_hj_pd.attrs.create("channel_dtype", "waveform")
        pm_201_hj_pd.attrs.create("x_units", "s")
        pm_201_hj_pd.attrs.create("y_units", "kJ")
        x = [1, 2, 3, 4, 5, 5456]
        y = [8, 3, 6, 2, 3, 8]
        pm_201_hj_pd.create_dataset("x", data=x)
        pm_201_hj_pd.create_dataset("y", data=y)


class TestHDFDataHandler:
    @pytest.mark.asyncio
    async def test_invalid_timestamp(self, remove_hdf_file):
        create_test_hdf_file(timestamp_test=True)

        instance = HDFDataHandler("test.h5")
        with pytest.raises(
            HDFDataExtractionError,
            match="Incorrect timestamp format for metadata timestamp. Use",
        ):
            await instance.extract_data()
