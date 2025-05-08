import io
import json
from unittest.mock import patch
from urllib.parse import quote
from zipfile import ZipFile

from fastapi import Response
from fastapi.testclient import TestClient
import imagehash
import numpy as np
from PIL import Image
import pytest

from operationsgateway_api.src.exceptions import EchoS3Error
from test.conftest import (
    assert_text_file_contents,
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
            "export_float_images",
            "export_vector_images",
            "export_vector_csvs",
            "lower_level",
            "upper_level",
            "colourmap_name",
            "expected_filename",
            "expected_filepath",
            "zip_contents_dict",
        ],
        [
            pytest.param(
                {
                    "_id": {
                        "$in": [
                            "20230605080000",
                            "20230605090000",
                            "20230605100000",
                            "20230605110000",
                            "20230605120000",
                        ],
                    },
                },
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
                "20230605080000_to_20230605120000.csv",
                "export/20230605080000_to_20230605120000_asc.csv",
                None,
                id="Basic CSV export of different channel types",
            ),
            pytest.param(
                {
                    "_id": {
                        "$in": [
                            "20230605080000",
                            "20230605090000",
                            "20230605100000",
                            "20230605110000",
                            "20230605120000",
                        ],
                    },
                },
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
                "20230605080000_to_20230605120000.csv",
                "export/20230605080000_to_20230605120000_desc.csv",
                None,
                id="Basic CSV export in descending shotnum order",
            ),
            pytest.param(
                {
                    "_id": {
                        "$in": [
                            "20230605080000",
                            "20230605090000",
                            "20230605100000",
                            "20230605110000",
                            "20230605120000",
                        ],
                    },
                },
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
                "20230605100000_to_20230605110000.csv",
                "export/20230605100000_to_20230605110000_desc_s_l.csv",
                None,
                id="Basic CSV export with skip and limit set",
            ),
            pytest.param(
                {
                    "_id": {
                        "$in": [
                            "20230605080000",
                            "20230605090000",
                            "20230605100000",
                            "20230605110000",
                            "20230605120000",
                        ],
                    },
                },
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
                "20230605080000_to_20230605120000.zip",
                None,
                {
                    "20230605080000_to_20230605120000.csv": "export/"
                    "20230605080000_to_20230605120000_asc.csv",
                    "20230605080000_FE-204-PSO-CAM-1.png": "da2d4927045f24bf",
                    "20230605090000_FE-204-PSO-CAM-1.png": "c8270437263f26bf",
                    "20230605100000_FE-204-PSO-CAM-1.png": "c8262437273b373d",
                    "20230605110000_FE-204-PSO-CAM-1.png": "da6d49270437247f",
                    "20230605120000_FE-204-PSO-CAM-1.png": "dad7495b04ab04fa",
                },
                id="Zip export of main CSV and images",
            ),
            pytest.param(
                {
                    "$and": [
                        {
                            "metadata.timestamp": {
                                "$gt": "2023-06-05T07:00:00",
                                "$lt": "2023-06-05T13:00:00",
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
                "20230605070600_to_20230605120000.csv",
                "export/20230605070600_to_20230605120000.csv",
                None,
                id="Basic CSV export of sparse data (some values missing)",
            ),
            pytest.param(
                {
                    "_id": {
                        "$in": [
                            "20230605080000",
                            "20230605090000",
                            "20230605100000",
                            "20230605110000",
                            "20230605120000",
                        ],
                    },
                },
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
                5,
                15,
                "jet_r",
                "20230605080000_to_20230605120000.zip",
                None,
                {
                    "20230605080000_to_20230605120000.csv": "export/"
                    "20230605080000_to_20230605120000_asc.csv",
                    "20230605080000_FE-204-PSO-CAM-1.png": "c73838c6c637c738",
                    "20230605090000_FE-204-PSO-CAM-1.png": "c73838c7c73838c7",
                    "20230605100000_FE-204-PSO-CAM-1.png": "c73838c7c73838c7",
                    "20230605110000_FE-204-PSO-CAM-1.png": "c73938c7c427c738",
                    "20230605120000_FE-204-PSO-CAM-1.png": "c4c43f273838c6fc",
                },
                id="Zip export of main CSV with images in false colour",
            ),
            pytest.param(
                {
                    "_id": {
                        "$in": [
                            "20230605080000",
                            "20230605090000",
                            "20230605100000",
                            "20230605110000",
                            "20230605120000",
                        ],
                    },
                },
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
                "20230605080000_to_20230605120000.zip",
                None,
                {
                    "20230605080000_to_20230605120000.csv": "export/"
                    "20230605080000_to_20230605120000_asc.csv",
                    "20230605080000_FE-204-PSO-CAM-1.png": "da2d4927045f24bf",
                    "20230605090000_FE-204-PSO-CAM-1.png": "c8270437263f26bf",
                    "20230605100000_FE-204-PSO-CAM-1.png": "c8262437273b373d",
                    "20230605110000_FE-204-PSO-CAM-1.png": "da6d49270437247f",
                    "20230605120000_FE-204-PSO-CAM-1.png": "dad7495b04ab04fa",
                    "20230605080000_FE-204-PSO-P1-SP.csv": "export/"
                    "20230605080000_FE-204-PSO-P1-SP.csv",
                    "20230605090000_FE-204-PSO-P1-SP.csv": "export/"
                    "20230605090000_FE-204-PSO-P1-SP.csv",
                    "20230605100000_FE-204-PSO-P1-SP.csv": "export/"
                    "20230605100000_FE-204-PSO-P1-SP.csv",
                    "20230605110000_FE-204-PSO-P1-SP.csv": "export/"
                    "20230605110000_FE-204-PSO-P1-SP.csv",
                    "20230605120000_FE-204-PSO-P1-SP.csv": "export/"
                    "20230605120000_FE-204-PSO-P1-SP.csv",
                },
                id="Zip export of main CSV, images & waveform CSVs",
            ),
            pytest.param(
                {
                    "_id": {
                        "$in": [
                            "20230605080000",
                            "20230605090000",
                            "20230605100000",
                            "20230605110000",
                            "20230605120000",
                        ],
                    },
                },
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
                "20230605080000_to_20230605120000.zip",
                None,
                {
                    "20230605080000_to_20230605120000.csv": "export/"
                    "20230605080000_to_20230605120000_asc.csv",
                    "20230605080000_FE-204-PSO-CAM-1.png": "da2d4927045f24bf",
                    "20230605090000_FE-204-PSO-CAM-1.png": "c8270437263f26bf",
                    "20230605100000_FE-204-PSO-CAM-1.png": "c8262437273b373d",
                    "20230605110000_FE-204-PSO-CAM-1.png": "da6d49270437247f",
                    "20230605120000_FE-204-PSO-CAM-1.png": "dad7495b04ab04fa",
                    "20230605080000_FE-204-PSO-P1-SP.csv": "export/"
                    "20230605080000_FE-204-PSO-P1-SP.csv",
                    "20230605090000_FE-204-PSO-P1-SP.csv": "export/"
                    "20230605090000_FE-204-PSO-P1-SP.csv",
                    "20230605100000_FE-204-PSO-P1-SP.csv": "export/"
                    "20230605100000_FE-204-PSO-P1-SP.csv",
                    "20230605110000_FE-204-PSO-P1-SP.csv": "export/"
                    "20230605110000_FE-204-PSO-P1-SP.csv",
                    "20230605120000_FE-204-PSO-P1-SP.csv": "export/"
                    "20230605120000_FE-204-PSO-P1-SP.csv",
                    "20230605080000_FE-204-PSO-P1-SP.png": "fa914e6e914eb04d",
                    "20230605090000_FE-204-PSO-P1-SP.png": "fa916e6e916e9181",
                    "20230605100000_FE-204-PSO-P1-SP.png": "fab14f6e914e90c1",
                    "20230605110000_FE-204-PSO-P1-SP.png": "fb914e6e914eb091",
                    "20230605120000_FE-204-PSO-P1-SP.png": "ff914e6e914eb081",
                },
                id="Zip export of main CSV, images, waveform CSVs and waveform images",
            ),
            pytest.param(
                {
                    "_id": {
                        "$in": [
                            "20230605080000",
                            "20230605090000",
                            "20230605100000",
                            "20230605110000",
                            "20230605120000",
                        ],
                    },
                },
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
                "20230605080000_to_20230605120000.zip",
                None,
                {
                    "20230605080000_to_20230605120000.csv": "export/"
                    "20230605080000_to_20230605120000_asc.csv",
                    "20230605080000_FE-204-PSO-P1-SP.csv": "export/"
                    "20230605080000_FE-204-PSO-P1-SP.csv",
                    "20230605090000_FE-204-PSO-P1-SP.csv": "export/"
                    "20230605090000_FE-204-PSO-P1-SP.csv",
                    "20230605100000_FE-204-PSO-P1-SP.csv": "export/"
                    "20230605100000_FE-204-PSO-P1-SP.csv",
                    "20230605110000_FE-204-PSO-P1-SP.csv": "export/"
                    "20230605110000_FE-204-PSO-P1-SP.csv",
                    "20230605120000_FE-204-PSO-P1-SP.csv": "export/"
                    "20230605120000_FE-204-PSO-P1-SP.csv",
                },
                id="Zip export of main CSV and waveform CSVs but no images",
            ),
            pytest.param(
                {
                    "_id": {
                        "$in": [
                            "20230605080000",
                            "20230605090000",
                            "20230605100000",
                            "20230605110000",
                            "20230605120000",
                        ],
                    },
                },
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
                None,
                None,
                None,
                None,
                None,
                None,
                "20230605080000_to_20230605120000.zip",
                None,
                {
                    "20230605080000_FE-204-PSO-CAM-1.png": "da2d4927045f24bf",
                    "20230605090000_FE-204-PSO-CAM-1.png": "c8270437263f26bf",
                    "20230605100000_FE-204-PSO-CAM-1.png": "c8262437273b373d",
                    "20230605110000_FE-204-PSO-CAM-1.png": "da6d49270437247f",
                    "20230605120000_FE-204-PSO-CAM-1.png": "dad7495b04ab04fa",
                },
                id="Zip export without main CSV so just images",
            ),
            pytest.param(
                {
                    "_id": {
                        "$in": [
                            "20230605080000",
                            "20230605090000",
                            "20230605100000",
                            "20230605110000",
                            "20230605120000",
                        ],
                    },
                },
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
                "20230605080000_to_20230605120000.zip",
                None,
                {
                    "20230605080000_to_20230605120000.csv": "export/"
                    "20230605080000_to_20230605120000_asc.csv",
                    "20230605080000_FE-204-PSO-CAM-1.png": "da2d4927045f24bf",
                    "20230605090000_FE-204-PSO-CAM-1.png": "c8270437263f26bf",
                    "20230605100000_FE-204-PSO-CAM-1.png": "c8262437273b373d",
                    "20230605110000_FE-204-PSO-CAM-1.png": "da6d49270437247f",
                    "20230605120000_FE-204-PSO-CAM-1.png": "dad7495b04ab04fa",
                },
                id="Zip export of main CSV and images but no waveform CSVs",
            ),
            pytest.param(
                {"_id": {"$in": ["20230605080300"]}},
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
                True,
                True,
                True,
                None,
                None,
                None,
                "20230605080300.zip",
                None,
                {
                    "20230605080300.csv": "export/20230605080300_asc.csv",
                    "20230605080300_FE-204-NSS-WFS.npz": (500, 680),
                    "20230605080300_FE-204-NSS-WFS-COEF.csv": (
                        "export/20230605080300_FE-204-NSS-WFS-COEF.csv"
                    ),
                    "20230605080300_FE-204-NSS-WFS-COEF.png": "9f87e03838c77c38",
                },
                id="Zip export of vector CSV/image and float images",
            ),
            pytest.param(
                {"_id": {"$in": ["20230605080300"]}},
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
                False,  # export_float_images
                True,  # export_vector_images
                True,  # export_vector_csvs
                None,
                None,
                None,
                "20230605080300.zip",
                None,
                {
                    "20230605080300.csv": "export/20230605080300_no_channels.csv",
                    "20230605080300_FE-204-LT-WFS-COEF.csv": (
                        "export/20230605080300_FE-204-LT-WFS-COEF.csv"
                    ),
                    "20230605080300_FE-204-LT-WFS-COEF.png": "9fc7c080719fcf60",
                },
                id="Zip export of vector CSV/image with labels",
            ),
            pytest.param(
                {"_id": {"$in": ["20230605080000"]}},
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
                "20230605080000.csv",
                "export/20230605080000.csv",
                None,
                id="CSV export of single record to test filename",
            ),
            pytest.param(
                {"_id": {"$in": ["20230605080000"]}},
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
                "20230605080000.zip",
                None,
                {
                    "20230605080000.csv": "export/20230605080000.csv",
                    "20230605080000_FE-204-PSO-CAM-1.png": "da2d4927045f24bf",
                },
                id="Zip export of single record to test filename",
            ),
            pytest.param(
                {
                    "_id": {
                        "$in": [
                            "20230605080000",
                            "20230605090000",
                            "20230605100000",
                            "20230605110000",
                            "20230605120000",
                        ],
                    },
                },
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
                "20230605080000_to_20230605120000_FE-204-PSO-EM.csv",
                "export/20230605080000_to_20230605120000_FE-204-PSO-EM.csv",
                None,
                id="CSV export of single channel to test filename",
            ),
            pytest.param(
                {"_id": {"$in": ["20230605080000"]}},
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
                "20230605080000_FE-204-PSO-CAM-1.zip",
                None,
                {
                    "20230605080000_FE-204-PSO-CAM-1.png": "da2d4927045f24bf",
                },
                id="Zip export of single channel to test filename",
            ),
            pytest.param(
                {
                    "_id": {
                        "$in": [
                            "20230605080000",
                            "20230605090000",
                            "20230605100000",
                            "20230605110000",
                            "20230605120000",
                        ],
                    },
                },
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
                "20230605080000_to_20230605120000_ID.csv",
                "export/20230605080000_to_20230605120000_ID.csv",
                None,
                id="CSV export of _id channel to test filename",
            ),
            pytest.param(
                {
                    "_id": {
                        "$in": [
                            "20230605080000",
                            "20230605090000",
                            "20230605100000",
                            "20230605110000",
                            "20230605120000",
                        ],
                    },
                },
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
                "20230605080000_to_20230605120000.csv",
                "export/20230605080000_to_20230605120000_asc_incl_id.csv",
                None,
                id="Basic CSV export of different channel types incl. _id channel",
            ),
            pytest.param(
                {
                    "_id": {
                        "$in": [
                            "20230605080000",
                            "20230605090000",
                            "20230605100000",
                            "20230605110000",
                            "20230605120000",
                        ],
                    },
                },
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
                "20230605080000_to_20230605120000.zip",
                None,
                {
                    "20230605080000_to_20230605120000.csv": "export/"
                    "20230605080000_to_20230605120000_functions.csv",
                    "20230605080000_image.png": "da2d4927045f24bf",
                    "20230605090000_image.png": "c8270437263f26bf",
                    "20230605100000_image.png": "c8262437273b373d",
                    "20230605110000_image.png": "da6d49270437247f",
                    "20230605120000_image.png": "dad7495b04ab04fa",
                    "20230605080000_waveform.csv": "export/"
                    "20230605080000_FE-204-PSO-P1-SP.csv",
                    "20230605090000_waveform.csv": "export/"
                    "20230605090000_FE-204-PSO-P1-SP.csv",
                    "20230605100000_waveform.csv": "export/"
                    "20230605100000_FE-204-PSO-P1-SP.csv",
                    "20230605110000_waveform.csv": "export/"
                    "20230605110000_FE-204-PSO-P1-SP.csv",
                    "20230605120000_waveform.csv": "export/"
                    "20230605120000_FE-204-PSO-P1-SP.csv",
                    "20230605080000_waveform.png": "fa914e6e914eb04d",
                    "20230605090000_waveform.png": "fa916e6e916e9181",
                    "20230605100000_waveform.png": "fab14f6e914e90c1",
                    "20230605110000_waveform.png": "fb914e6e914eb091",
                    "20230605120000_waveform.png": "ff914e6e914eb081",
                },
                id=(
                    "Zip export of main CSV, images, waveform CSVs and "
                    "waveform images using functions"
                ),
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
        export_float_images: bool,
        export_vector_images: bool,
        export_vector_csvs: bool,
        lower_level,
        upper_level,
        colourmap_name,
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
        TestExport.compile_functions(get_params, "scalar", "FE-204-PSO-EM + 1")
        TestExport.compile_functions(
            get_params,
            "waveform",
            "FE-204-PSO-P1-SP + (1 - 1)",
        )
        TestExport.compile_functions(get_params, "image", "FE-204-PSO-CAM-1 + (1 - 1)")

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
            assert_text_file_contents(expected_filepath, test_response.text)
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

    def test_export_errors(
        self,
        test_app: TestClient,
        login_and_get_token,
    ):
        get_params = [
            f"conditions={json.dumps({'_id': {'$eq': '20230605080300'}})}",
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
            "20230605080300.zip",
        )
        zip_contents_dict = {"EXPORT_ERRORS.txt": "export/EXPORT_ERRORS.txt"}
        TestExport.check_zip_file_contents(zip_contents_dict, test_response)

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
        conditions = {"_id": {"$in": ["20230605080000"]}}
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
    def compile_functions(get_params: list, name: str, expression: str) -> None:
        function_str = json.dumps({"name": name, "expression": expression})
        TestExport.compile_get_params(get_params, "functions", quote(function_str))

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
                if filename_in_zip.endswith(".csv") or filename_in_zip.endswith(".txt"):
                    # there should be a file in the test dir that the contents of the
                    # CSV in the zip file need comparing to
                    assert_text_file_contents(
                        filepath_or_hash,
                        zip_file.open(filename_in_zip).read().decode(),
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
