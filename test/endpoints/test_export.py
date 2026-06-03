import io
import json
from unittest.mock import patch
from urllib.parse import quote
from zipfile import ZipFile

from fastapi.testclient import TestClient
from httpx import Response
import imagehash
import numpy as np
from PIL import Image
import pytest

from operationsgateway_api.src.exceptions import EchoS3Error
from test.conftest import (
    assert_text_file_contents,
    MARK_EPAC_TEST,
    MARK_GEMINI_TEST,
    RECORD_ID_05_0800,
    RECORD_ID_05_0803,
    RECORD_ID_05_1700,
)


class TestExport:
    @pytest.mark.parametrize(
        [
            "conditions",
            "skip",
            "limit",
            "order",
            "projection",
            "export_waveform_images",
            "export_waveform_csvs",
            "export_images",
            "export_scalars",
            "export_strings",
            "export_float_images",
            "export_vector_images",
            "export_vector_csvs",
            "lower_level",
            "upper_level",
            "colourmap_name",
            "functions",
            "expected_filename",
            "expected_filepath",
            "zip_contents_dict",
        ],
        [
            pytest.param(
                {"_id": {"$in": [RECORD_ID_05_0800, RECORD_ID_05_0803]}},
                0,
                10,
                "metadata.shotnum ASC",
                # shotnum, timestamp and epac_ops_data_version provide examples of
                # integer, timestamp and string fields which are exported differently
                # to CSV
                [
                    "metadata.shotnum",
                    "metadata.timestamp",
                    "metadata.epac_ops_data_version",
                    "channels.FE-204-PSO-EM.data",
                ],
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                [],  # functions
                f"{RECORD_ID_05_0800}_to_{RECORD_ID_05_0803}.csv",
                f"export/{RECORD_ID_05_0800}_to_{RECORD_ID_05_0803}.csv",
                None,
                id="Basic CSV export of different channel types",
            ),
            pytest.param(
                {"_id": {"$in": [RECORD_ID_05_0800, RECORD_ID_05_0803]}},
                0,
                10,
                "metadata.shotnum DESC",
                [
                    "metadata.shotnum",
                    "metadata.timestamp",
                    "metadata.epac_ops_data_version",
                    "channels.FE-204-PSO-EM.data",
                ],
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                [],  # functions
                f"{RECORD_ID_05_0800}_to_{RECORD_ID_05_0803}.csv",
                f"export/{RECORD_ID_05_0800}_to_{RECORD_ID_05_0803}_desc.csv",
                None,
                id="Basic CSV export in descending shotnum order",
            ),
            pytest.param(
                {"_id": {"$in": [RECORD_ID_05_0800, RECORD_ID_05_0803]}},
                1,
                2,
                "metadata.shotnum DESC",
                [
                    "metadata.shotnum",
                    "metadata.timestamp",
                    "metadata.epac_ops_data_version",
                    "channels.FE-204-PSO-EM.data",
                ],
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                [],  # functions
                f"{RECORD_ID_05_0800}.csv",
                f"export/{RECORD_ID_05_0800}.csv",
                None,
                id="Basic CSV export with skip and limit set",
            ),
            pytest.param(
                {"_id": {"$in": [RECORD_ID_05_0800, RECORD_ID_05_0803]}},
                0,
                10,
                "metadata.shotnum ASC",
                [
                    "metadata.shotnum",
                    "metadata.timestamp",
                    "metadata.epac_ops_data_version",
                    "channels.FE-204-PSO-EM.data",
                    "channels.FE-204-PSO-CAM-1",
                ],
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                [],  # functions
                f"{RECORD_ID_05_0800}_to_{RECORD_ID_05_0803}.zip",
                None,
                {
                    f"{RECORD_ID_05_0800}_to_{RECORD_ID_05_0803}.csv": (
                        f"export/{RECORD_ID_05_0800}_to_{RECORD_ID_05_0803}.csv"
                    ),
                    f"{RECORD_ID_05_0800}_FE-204-PSO-CAM-1.png": "da2d4927045f24bf",
                    f"{RECORD_ID_05_0803}_FE-204-PSO-CAM-1.png": "d5b55a554aaa4a55",
                },
                id="Zip export of main CSV and images",
            ),
            pytest.param(
                {
                    "$and": [
                        {
                            "metadata.timestamp": {
                                "$gt": "2023-06-05T07:00:00",
                                "$lt": "2023-06-05T18:00:00",
                            },
                        },
                    ],
                },
                None,
                None,
                None,
                [
                    "metadata.shotnum",
                    "metadata.timestamp",
                    "metadata.epac_ops_data_version",
                    "channels.FE-204-PSO-EM.data",
                ],
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                [],  # functions
                f"{RECORD_ID_05_0800}_to_{RECORD_ID_05_1700}.csv",
                f"export/{RECORD_ID_05_0800}_to_{RECORD_ID_05_1700}.csv",
                None,
                id="Basic CSV export of sparse data (some values missing)",
            ),
            pytest.param(
                {"_id": {"$in": [RECORD_ID_05_0800, RECORD_ID_05_0803]}},
                0,
                10,
                "metadata.shotnum ASC",
                [
                    "metadata.shotnum",
                    "metadata.timestamp",
                    "metadata.epac_ops_data_version",
                    "channels.FE-204-PSO-EM.data",
                    "channels.FE-204-PSO-CAM-1",
                ],
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                5,
                15,
                "jet_r",
                [],  # functions
                f"{RECORD_ID_05_0800}_to_{RECORD_ID_05_0803}.zip",
                None,
                {
                    f"{RECORD_ID_05_0800}_to_{RECORD_ID_05_0803}.csv": (
                        f"export/{RECORD_ID_05_0800}_to_{RECORD_ID_05_0803}.csv"
                    ),
                    f"{RECORD_ID_05_0800}_FE-204-PSO-CAM-1.png": "c73838c6c637c738",
                    f"{RECORD_ID_05_0803}_FE-204-PSO-CAM-1.png": "b624db22fb26d903",
                },
                id="Zip export of main CSV with images in false colour",
            ),
            pytest.param(
                {"_id": {"$in": [RECORD_ID_05_0800, RECORD_ID_05_0803]}},
                0,
                10,
                "metadata.shotnum ASC",
                # including a waveform channel to add waveform CSV files to export
                [
                    "metadata.shotnum",
                    "metadata.timestamp",
                    "metadata.epac_ops_data_version",
                    "channels.FE-204-PSO-EM.data",
                    "channels.FE-204-PSO-CAM-1",
                    "channels.FE-204-PSO-P1-SP",
                ],
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                [],  # functions
                f"{RECORD_ID_05_0800}_to_{RECORD_ID_05_0803}.zip",
                None,
                {
                    f"{RECORD_ID_05_0800}_to_{RECORD_ID_05_0803}.csv": (
                        f"export/{RECORD_ID_05_0800}_to_{RECORD_ID_05_0803}.csv"
                    ),
                    f"{RECORD_ID_05_0800}_FE-204-PSO-CAM-1.png": "da2d4927045f24bf",
                    f"{RECORD_ID_05_0800}_FE-204-PSO-P1-SP.csv": (
                        "export/20230605080000_FE-204-PSO-P1-SP.csv"
                    ),
                    f"{RECORD_ID_05_0803}_FE-204-PSO-CAM-1.png": "d5b55a554aaa4a55",
                    f"{RECORD_ID_05_0803}_FE-204-PSO-P1-SP.csv": (
                        "export/20230605080300_FE-204-PSO-P1-SP.csv"
                    ),
                },
                id="Zip export of main CSV, images & waveform CSVs",
            ),
            pytest.param(
                {"_id": {"$in": [RECORD_ID_05_0800, RECORD_ID_05_0803]}},
                0,
                10,
                "metadata.shotnum ASC",
                # including a waveform channel to add waveform CSV and waveform image
                # files to export
                [
                    "metadata.shotnum",
                    "metadata.timestamp",
                    "metadata.epac_ops_data_version",
                    "channels.FE-204-PSO-EM.data",
                    "channels.FE-204-PSO-CAM-1",
                    "channels.FE-204-PSO-P1-SP",
                ],
                True,  # export_waveform_images - request these
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                [],  # functions
                f"{RECORD_ID_05_0800}_to_{RECORD_ID_05_0803}.zip",
                None,
                {
                    f"{RECORD_ID_05_0800}_to_{RECORD_ID_05_0803}.csv": (
                        f"export/{RECORD_ID_05_0800}_to_{RECORD_ID_05_0803}.csv"
                    ),
                    f"{RECORD_ID_05_0800}_FE-204-PSO-CAM-1.png": "da2d4927045f24bf",
                    f"{RECORD_ID_05_0800}_FE-204-PSO-P1-SP.csv": (
                        "export/20230605080000_FE-204-PSO-P1-SP.csv"
                    ),
                    f"{RECORD_ID_05_0800}_FE-204-PSO-P1-SP.png": "fa914e6e914eb04d",
                    f"{RECORD_ID_05_0803}_FE-204-PSO-CAM-1.png": "d5b55a554aaa4a55",
                    f"{RECORD_ID_05_0803}_FE-204-PSO-P1-SP.csv": (
                        "export/20230605080300_FE-204-PSO-P1-SP.csv"
                    ),
                    f"{RECORD_ID_05_0803}_FE-204-PSO-P1-SP.png": "fa916e6e916e9181",
                },
                id="Zip export of main CSV, images, waveform CSVs and waveform images",
            ),
            pytest.param(
                {"_id": {"$in": [RECORD_ID_05_0800, RECORD_ID_05_0803]}},
                0,
                10,
                "metadata.shotnum ASC",
                [
                    "metadata.shotnum",
                    "metadata.timestamp",
                    "metadata.epac_ops_data_version",
                    "channels.FE-204-PSO-EM.data",
                    "channels.FE-204-PSO-CAM-1",
                    "channels.FE-204-PSO-P1-SP",
                ],
                None,
                None,
                False,  # don't export images
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                [],  # functions
                f"{RECORD_ID_05_0800}_to_{RECORD_ID_05_0803}.zip",
                None,
                {
                    f"{RECORD_ID_05_0800}_to_{RECORD_ID_05_0803}.csv": (
                        f"export/{RECORD_ID_05_0800}_to_{RECORD_ID_05_0803}.csv"
                    ),
                    f"{RECORD_ID_05_0800}_FE-204-PSO-P1-SP.csv": (
                        "export/20230605080000_FE-204-PSO-P1-SP.csv"
                    ),
                    f"{RECORD_ID_05_0803}_FE-204-PSO-P1-SP.csv": (
                        "export/20230605080300_FE-204-PSO-P1-SP.csv"
                    ),
                },
                id="Zip export of main CSV and waveform CSVs but no images",
            ),
            pytest.param(
                {"_id": {"$in": [RECORD_ID_05_0800, RECORD_ID_05_0803]}},
                0,
                10,
                "metadata.shotnum ASC",
                [
                    "metadata.shotnum",
                    "metadata.timestamp",
                    "metadata.epac_ops_data_version",
                    "channels.FE-204-PSO-EM.data",
                    "channels.FE-204-PSO-CAM-1",
                ],
                None,
                None,
                None,
                False,  # export_scalars - don't export the main CSV file
                False,  # export_strings
                None,
                None,
                None,
                None,
                None,
                None,
                [],  # functions
                f"{RECORD_ID_05_0800}_to_{RECORD_ID_05_0803}.zip",
                None,
                {
                    f"{RECORD_ID_05_0800}_FE-204-PSO-CAM-1.png": "da2d4927045f24bf",
                    f"{RECORD_ID_05_0803}_FE-204-PSO-CAM-1.png": "d5b55a554aaa4a55",
                },
                id="Zip export without main CSV so just images",
            ),
            pytest.param(
                {"_id": {"$in": [RECORD_ID_05_0800, RECORD_ID_05_0803]}},
                0,
                10,
                "metadata.shotnum ASC",
                [
                    "metadata.shotnum",
                    "metadata.timestamp",
                    "metadata.epac_ops_data_version",
                    "channels.FE-204-PSO-EM.data",
                    "channels.FE-204-PSO-CAM-1",
                    "channels.FE-204-PSO-P1-SP",
                ],
                None,
                False,  # export_waveform_csvs - don't export these
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                [],  # functions
                f"{RECORD_ID_05_0800}_to_{RECORD_ID_05_0803}.zip",
                None,
                {
                    f"{RECORD_ID_05_0800}_to_{RECORD_ID_05_0803}.csv": (
                        f"export/{RECORD_ID_05_0800}_to_{RECORD_ID_05_0803}.csv"
                    ),
                    f"{RECORD_ID_05_0800}_FE-204-PSO-CAM-1.png": "da2d4927045f24bf",
                    f"{RECORD_ID_05_0803}_FE-204-PSO-CAM-1.png": "d5b55a554aaa4a55",
                },
                id="Zip export of main CSV and images but no waveform CSVs",
            ),
            pytest.param(
                {"_id": {"$in": [RECORD_ID_05_0803]}},
                0,
                10,
                "metadata.shotnum ASC",
                [
                    "metadata.shotnum",
                    "metadata.timestamp",
                    "metadata.epac_ops_data_version",
                    "channels.FE-204-PSO-EM.data",
                    "channels.FE-204-NSS-WFS",
                    "channels.FE-204-NSS-WFS-COEF",
                ],
                None,
                None,
                None,
                None,
                None,
                True,
                True,
                True,
                None,
                None,
                None,
                [],  # functions
                f"{RECORD_ID_05_0803}.zip",
                None,
                {
                    f"{RECORD_ID_05_0803}.csv": f"export/{RECORD_ID_05_0803}.csv",
                    f"{RECORD_ID_05_0803}_FE-204-NSS-WFS.npz": (500, 680),
                    f"{RECORD_ID_05_0803}_FE-204-NSS-WFS-COEF.csv": (
                        "export/20230605080300_FE-204-NSS-WFS-COEF.csv"
                    ),
                    f"{RECORD_ID_05_0803}_FE-204-NSS-WFS-COEF.png": "9f87e03838c77c38",
                },
                id="Zip export of vector CSV/image and float images",
            ),
            pytest.param(
                {"_id": {"$in": [RECORD_ID_05_0803]}},
                0,
                10,
                "metadata.shotnum ASC",
                [
                    "metadata.shotnum",
                    "metadata.timestamp",
                    "metadata.epac_ops_data_version",
                    "channels.FE-204-LT-WFS",
                    "channels.FE-204-LT-WFS-COEF",
                ],
                None,
                None,
                None,
                None,
                None,
                False,  # export_float_images
                True,  # export_vector_images
                True,  # export_vector_csvs
                None,
                None,
                None,
                [],  # functions
                f"{RECORD_ID_05_0803}.zip",
                None,
                {
                    f"{RECORD_ID_05_0803}.csv": (
                        f"export/{RECORD_ID_05_0803}_no_channels.csv"
                    ),
                    f"{RECORD_ID_05_0803}_FE-204-LT-WFS-COEF.csv": (
                        "export/20230605080300_FE-204-LT-WFS-COEF.csv"
                    ),
                    f"{RECORD_ID_05_0803}_FE-204-LT-WFS-COEF.png": "9fc7c080719fcf60",
                },
                id="Zip export of vector CSV/image with labels",
            ),
            pytest.param(
                {"_id": {"$in": [RECORD_ID_05_0800]}},
                0,
                10,
                "metadata.shotnum ASC",
                [
                    "metadata.shotnum",
                    "metadata.timestamp",
                    "metadata.epac_ops_data_version",
                    "channels.FE-204-PSO-EM.data",
                ],
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                [],  # functions
                f"{RECORD_ID_05_0800}.csv",
                f"export/{RECORD_ID_05_0800}.csv",
                None,
                id="CSV export of single record to test filename",
            ),
            pytest.param(
                {"_id": {"$in": [RECORD_ID_05_0800]}},
                None,
                None,
                None,
                [
                    "metadata.shotnum",
                    "metadata.timestamp",
                    "metadata.epac_ops_data_version",
                    "channels.FE-204-PSO-EM.data",
                    "channels.FE-204-PSO-CAM-1",
                ],
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                [],  # functions
                f"{RECORD_ID_05_0800}.zip",
                None,
                {
                    f"{RECORD_ID_05_0800}.csv": f"export/{RECORD_ID_05_0800}.csv",
                    f"{RECORD_ID_05_0800}_FE-204-PSO-CAM-1.png": "da2d4927045f24bf",
                },
                id="Zip export of single record to test filename",
            ),
            pytest.param(
                {"_id": {"$in": [RECORD_ID_05_0800, RECORD_ID_05_0803]}},
                0,
                10,
                "metadata.shotnum ASC",
                ["channels.FE-204-PSO-EM.data"],
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                [],  # functions
                f"{RECORD_ID_05_0800}_to_{RECORD_ID_05_0803}_FE-204-PSO-EM.csv",
                f"export/{RECORD_ID_05_0800}_to_{RECORD_ID_05_0803}_FE-204-PSO-EM.csv",
                None,
                id="CSV export of single channel to test filename",
            ),
            pytest.param(
                {"_id": {"$in": [RECORD_ID_05_0800]}},
                None,
                None,
                None,
                ["channels.FE-204-PSO-CAM-1"],
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                [],  # functions
                f"{RECORD_ID_05_0800}_FE-204-PSO-CAM-1.zip",
                None,
                {
                    f"{RECORD_ID_05_0800}_FE-204-PSO-CAM-1.png": "da2d4927045f24bf",
                },
                id="Zip export of single channel to test filename",
            ),
            pytest.param(
                {"_id": {"$in": [RECORD_ID_05_0800, RECORD_ID_05_0803]}},
                0,
                10,
                "metadata.shotnum ASC",
                ["_id"],
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                [],  # functions
                f"{RECORD_ID_05_0800}_to_{RECORD_ID_05_0803}_ID.csv",
                f"export/{RECORD_ID_05_0800}_to_{RECORD_ID_05_0803}_ID.csv",
                None,
                id="CSV export of _id channel to test filename",
            ),
            pytest.param(
                {"_id": {"$in": [RECORD_ID_05_0800, RECORD_ID_05_0803]}},
                0,
                10,
                "metadata.shotnum ASC",
                # _id is a special case and handled differently to other channels
                [
                    "_id",
                    "metadata.shotnum",
                    "metadata.timestamp",
                    "metadata.epac_ops_data_version",
                    "channels.FE-204-PSO-EM.data",
                ],
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                [],  # functions
                f"{RECORD_ID_05_0800}_to_{RECORD_ID_05_0803}.csv",
                f"export/{RECORD_ID_05_0800}_to_{RECORD_ID_05_0803}_incl_id.csv",
                None,
                id="Basic CSV export of different channel types incl. _id channel",
            ),
            pytest.param(
                {"_id": {"$in": [RECORD_ID_05_0800, RECORD_ID_05_0803]}},
                0,
                10,
                "metadata.shotnum ASC",
                # including a waveform channel to add waveform CSV and waveform image
                # files to export
                [
                    "metadata.shotnum",
                    "metadata.timestamp",
                    "metadata.epac_ops_data_version",
                    "channels.FE-204-PSO-EM.data",
                    "channels.FE-204-PSO-CAM-1",
                    "channels.FE-204-PSO-P1-SP",
                ],
                True,  # export_waveform_images - request these
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                [
                    {"name": "scalar", "expression": "FE-204-PSO-EM + 1"},
                    {"name": "waveform", "expression": "FE-204-PSO-P1-SP + (1 - 1)"},
                    {"name": "image", "expression": "FE-204-PSO-CAM-1 + (1 - 1)"},
                ],
                f"{RECORD_ID_05_0800}_to_{RECORD_ID_05_0803}.zip",
                None,
                {
                    f"{RECORD_ID_05_0800}_to_{RECORD_ID_05_0803}.csv": (
                        f"export/{RECORD_ID_05_0800}_to_{RECORD_ID_05_0803}.csv"
                    ),
                    f"{RECORD_ID_05_0800}_FE-204-PSO-CAM-1.png": "da2d4927045f24bf",
                    f"{RECORD_ID_05_0800}_FE-204-PSO-P1-SP.csv": (
                        "export/20230605080000_FE-204-PSO-P1-SP.csv"
                    ),
                    f"{RECORD_ID_05_0800}_FE-204-PSO-P1-SP.png": "fa914e6e914eb04d",
                    f"{RECORD_ID_05_0803}_FE-204-PSO-CAM-1.png": "d5b55a554aaa4a55",
                    f"{RECORD_ID_05_0803}_FE-204-PSO-P1-SP.csv": (
                        "export/20230605080300_FE-204-PSO-P1-SP.csv"
                    ),
                    f"{RECORD_ID_05_0803}_FE-204-PSO-P1-SP.png": "fa916e6e916e9181",
                },
                id=(
                    "Zip export of main CSV, images, waveform CSVs and waveform images "
                    "with functions defined but not included in projections"
                ),
            ),
            pytest.param(
                {"_id": {"$in": [RECORD_ID_05_0800, RECORD_ID_05_0803]}},
                0,
                10,
                "metadata.shotnum ASC",
                # including a waveform channel to add waveform CSV files to export
                [
                    "metadata.shotnum",
                    "metadata.timestamp",
                    "metadata.epac_ops_data_version",
                    "channels.scalar.data",
                    "channels.waveform",
                    "channels.image",
                ],
                True,  # export_waveform_images - request these
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                [
                    {"name": "scalar", "expression": "FE-204-PSO-EM + 1"},
                    {"name": "waveform", "expression": "FE-204-PSO-P1-SP + (1 - 1)"},
                    {"name": "image", "expression": "FE-204-PSO-CAM-1 + (1 - 1)"},
                ],
                f"{RECORD_ID_05_0800}_to_{RECORD_ID_05_0803}.zip",
                None,
                {
                    f"{RECORD_ID_05_0800}_to_{RECORD_ID_05_0803}.csv": (
                        f"export/{RECORD_ID_05_0800}_to_{RECORD_ID_05_0803}_functions.csv"
                    ),
                    f"{RECORD_ID_05_0800}_image.png": "da2d4927045f24bf",
                    f"{RECORD_ID_05_0800}_waveform.csv": (
                        "export/20230605080000_FE-204-PSO-P1-SP.csv"
                    ),
                    f"{RECORD_ID_05_0800}_waveform.png": "fa914e6e914eb04d",
                    f"{RECORD_ID_05_0803}_image.png": "d5b55a554aaa4a55",
                    f"{RECORD_ID_05_0803}_waveform.csv": (
                        "export/20230605080300_FE-204-PSO-P1-SP.csv"
                    ),
                    f"{RECORD_ID_05_0803}_waveform.png": "fa916e6e916e9181",
                },
                id=(
                    "Zip export of main CSV, images, waveform CSVs and "
                    "waveform images using functions"
                ),
            ),
            pytest.param(
                {"_id": {"$in": [RECORD_ID_05_0800, RECORD_ID_05_0803]}},
                0,
                10,
                "metadata.shotnum ASC",
                [
                    "metadata.shotnum",
                    "metadata.timestamp",
                    "metadata.epac_ops_data_version",
                    "channels.FE-204-PSO-EM.data",
                    "channels.FE-204-PSO-CAM-1",
                ],
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                5,
                15,
                "jet_r",
                [
                    {"name": "image", "expression": "FE-204-PSO-CAM-1 + (1 - 1)"},
                ],
                f"{RECORD_ID_05_0800}_to_{RECORD_ID_05_0803}.zip",
                None,
                {
                    f"{RECORD_ID_05_0800}_to_{RECORD_ID_05_0803}.csv": (
                        f"export/{RECORD_ID_05_0800}_to_{RECORD_ID_05_0803}.csv"
                    ),
                    f"{RECORD_ID_05_0800}_FE-204-PSO-CAM-1.png": "c73838c6c637c738",
                    f"{RECORD_ID_05_0803}_FE-204-PSO-CAM-1.png": "b624db22fb26d903",
                },
                id=(
                    "Zip export of main CSV with images in false colour "
                    "with functions defined but not included in projections"
                ),
            ),
            pytest.param(
                {"_id": {"$in": [RECORD_ID_05_0800, RECORD_ID_05_0803]}},
                0,
                10,
                "metadata.shotnum ASC",
                [
                    "metadata.shotnum",
                    "metadata.timestamp",
                    "metadata.epac_ops_data_version",
                    "channels.ASTRA_CONTROL_MODE_STRING.data",
                ],
                None,
                None,
                None,
                None,
                True,  # export_strings
                None,
                None,
                None,
                None,
                None,
                None,
                [],  # functions
                f"{RECORD_ID_05_0800}_to_{RECORD_ID_05_0803}_ASTRA_CONTROL_MODE_STRING.csv",
                f"export/{RECORD_ID_05_0800}_to_{RECORD_ID_05_0803}_ASTRA_CONTROL_MODE_STRING.csv",
                None,
                marks=MARK_GEMINI_TEST,
                id="CSV export of string channel",
            ),
        ],
    )
    def test_csv_export(
        self,
        test_app: TestClient,
        login_and_get_token,
        conditions,
        skip,
        limit,
        order,
        projection,
        export_waveform_images,
        export_waveform_csvs,
        export_images,
        export_scalars,
        export_strings,
        export_float_images: bool,
        export_vector_images: bool,
        export_vector_csvs: bool,
        lower_level,
        upper_level,
        colourmap_name,
        functions: list[dict[str, str]],
        expected_filename,
        expected_filepath,
        zip_contents_dict,
    ):
        get_params = []

        if isinstance(projection, list):
            for field_name in projection:
                get_params.append(f"projection={field_name}")

        get_params.append(f"conditions={json.dumps(conditions)}")

        TestExport.compile_get_params(get_params, "skip", skip)
        TestExport.compile_get_params(get_params, "limit", limit)
        TestExport.compile_get_params(get_params, "order", order)
        TestExport.compile_get_params(
            get_params,
            "export_waveform_images",
            export_waveform_images,
        )
        TestExport.compile_get_params(
            get_params,
            "export_waveform_csvs",
            export_waveform_csvs,
        )
        TestExport.compile_get_params(get_params, "export_images", export_images)
        TestExport.compile_get_params(get_params, "export_scalars", export_scalars)
        TestExport.compile_get_params(get_params, "export_strings", export_strings)
        TestExport.compile_get_params(
            get_params,
            "export_float_images",
            export_float_images,
        )
        TestExport.compile_get_params(
            get_params,
            "export_vector_images",
            export_vector_images,
        )
        TestExport.compile_get_params(
            get_params,
            "export_vector_csvs",
            export_vector_csvs,
        )
        TestExport.compile_get_params(get_params, "lower_level", lower_level)
        TestExport.compile_get_params(get_params, "upper_level", upper_level)
        TestExport.compile_get_params(get_params, "colourmap_name", colourmap_name)
        for function in functions:
            value = quote(json.dumps(function))
            TestExport.compile_get_params(get_params, "functions", value)

        get_params_str = "&".join(get_params)

        test_response = test_app.get(
            f"/export?{get_params_str}",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        if expected_filename.endswith(".csv"):
            TestExport.check_export_headers(
                test_response,
                "text/plain",
                expected_filename,
            )
            with open(f"test/{expected_filepath}") as f:
                assert f.read() == test_response.text

        elif expected_filename.endswith(".zip"):
            TestExport.check_export_headers(
                test_response,
                "application/zip",
                expected_filename,
            )
            TestExport.check_zip_file_contents(zip_contents_dict, test_response)

        else:
            raise AssertionError(f"Unexpected file type: {expected_filename}")

        assert test_response.status_code == 200

    @pytest.mark.parametrize(
        ["file_prefix"],
        [
            pytest.param("EPAC_", marks=MARK_EPAC_TEST),
            pytest.param("GEMINI_", marks=MARK_GEMINI_TEST),
        ],
    )
    def test_export_errors(
        self,
        test_app: TestClient,
        login_and_get_token,
        file_prefix: str,
    ):
        get_params = [
            f"conditions={json.dumps({'_id': {'$eq': RECORD_ID_05_0803}})}",
            "projection=metadata.shotnum",
            "projection=metadata.timestamp",
            "projection=metadata.epac_ops_data_version",
            "projection=channels.FE-204-PSO-EM",
            "projection=channels.FE-204-LT-WFS",
            "projection=channels.FE-204-LT-WFS-COEF",
        ]
        get_params_str = "&".join(get_params)

        target = (
            "operationsgateway_api.src.records.echo_interface.EchoInterface."
            "download_file_object"
        )
        with patch(target=target, side_effect=EchoS3Error()):
            test_response = test_app.get(
                f"/export?{get_params_str}",
                headers={"Authorization": f"Bearer {login_and_get_token}"},
            )

        TestExport.check_export_headers(
            test_response,
            "application/zip",
            f"{RECORD_ID_05_0803}.zip",
        )
        TestExport.check_zip_file_contents(
            zip_contents_dict={
                "EXPORT_ERRORS.txt": f"export/{file_prefix}EXPORT_ERRORS.txt",
            },
            response=test_response,
        )

    @pytest.mark.parametrize(
        ["projection", "message"],
        [
            pytest.param(
                "channels",
                "Projection 'channels' did not include a second term",
            ),
            pytest.param(
                "channels.non_existent_channel",
                "'non_existent_channel' is not a recognised channel or function name",
            ),
        ],
    )
    def test_csv_export_failure(
        self,
        test_app: TestClient,
        login_and_get_token: str,
        projection: str,
        message: str,
    ):
        get_params = []
        conditions = {"_id": {"$in": [RECORD_ID_05_0800]}}
        get_params.append(f"conditions={json.dumps(conditions)}")
        get_params.append(f"projection={projection}")
        TestExport.compile_get_params(get_params, "skip", 0)
        TestExport.compile_get_params(get_params, "limit", 1)
        TestExport.compile_get_params(get_params, "order", "metadata.shotnum ASC")
        get_params_str = "&".join(get_params)

        test_response = test_app.get(
            f"/export?{get_params_str}",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_response.status_code == 400
        assert json.loads(test_response.content.decode())["detail"] == message

    @staticmethod
    def compile_get_params(get_params: list, param_name: str, param_value: str):
        """
        If a value is set for the parameter passed in then add it to the list of
        name-value pair strings that is being compiled to form the get query string
        """
        if param_value is not None:
            get_params.append(f"{param_name}={param_value}")

    @staticmethod
    def check_export_headers(
        response: Response,
        content_type: str,
        expected_filename: str,
    ):
        """
        Check that there is a content disposition header in the response and that it
        indicates that there will be an attachment with the specified filename.
        """
        try:
            type_header = response.headers["content-type"]
        except KeyError as err:
            raise AssertionError("No 'content-type' header found") from err
        assert content_type in type_header
        try:
            disposition_header = response.headers["content-disposition"]
        except KeyError as err:
            raise AssertionError("No 'content-disposition' header found") from err
        assert disposition_header == f'attachment; filename="{expected_filename}"'

    @staticmethod
    def check_zip_file_contents(
        zip_contents_dict: "dict[str, str]",
        response: Response,
    ):
        """
        Check that the contents of an exported zip file are as expected.
        The zip_contents_dict contains a list of all the files that the zip should
        contain.
        CSV files will have a path to where a file containing the expected contents can
        be found.
        Images will have a perceptual hash which can be checked to ensure the image is
        as expected.
        """
        with ZipFile(io.BytesIO(response.content)) as zip_file:
            filenames_in_zip = []
            for zip_info in zip_file.infolist():
                filename_in_zip = zip_info.filename
                filenames_in_zip.append(filename_in_zip)
                try:
                    filepath_or_hash = zip_contents_dict[filename_in_zip]
                except KeyError as err:
                    raise AssertionError(
                        f"Unexpected file found in export zip: {filename_in_zip}",
                    ) from err
                if filename_in_zip.endswith(".txt"):
                    assert_text_file_contents(
                        filepath_or_hash,
                        zip_file.open(filename_in_zip).readlines(),
                        sort_lines=True,
                    )
                elif filename_in_zip.endswith(".csv"):
                    # there should be a file in the test dir that the contents of the
                    # CSV in the zip file need comparing to
                    assert_text_file_contents(
                        filepath_or_hash,
                        zip_file.open(filename_in_zip).readlines(),
                    )
                elif filename_in_zip.endswith(".png"):
                    # this is an image so it needs a perceptual hash generating and
                    # comparing with what is expected
                    image = Image.open(zip_file.open(filename_in_zip))
                    phash = str(imagehash.phash(image))
                    assert filepath_or_hash == phash
                elif filename_in_zip.endswith(".npz"):
                    array = np.load(zip_file.open(filename_in_zip))["arr_0"]
                    assert array.shape == filepath_or_hash
                else:
                    raise ValueError(f"Unexpected file extension for {filename_in_zip}")
            # diff the expected file list with that found in the zip
            # to check that all expected files were present
            files_diff = [
                filename
                for filename in zip_contents_dict.keys()
                if filename not in filenames_in_zip
            ]
            assert len(zip_contents_dict) == len(
                zip_file.infolist(),
            ), f"Missing files in export zip: {files_diff}"
