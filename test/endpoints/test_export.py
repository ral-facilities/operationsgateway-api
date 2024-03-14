import io
import json
from zipfile import ZipFile

from fastapi import Response
from fastapi.testclient import TestClient
import imagehash
from PIL import Image
import pytest

from test.conftest import (
    assert_text_file_contents,
)


class TestExport:
    @pytest.mark.parametrize(
        "conditions, skip, limit, order, projection, "
        "export_waveform_images, export_waveform_csvs, export_images, export_scalars, "
        "lower_level, upper_level, colourmap_name, "
        "expected_filename, expected_filepath, zip_contents_dict",
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
                5,
                15,
                "jet_r",
                "20230605080000_to_20230605120000.zip",
                None,
                {
                    "20230605080000_to_20230605120000.csv": "export/"
                    "20230605080000_to_20230605120000_asc.csv",
                    "20230605080000_FE-204-PSO-CAM-1.png": "c73838c7c437c738",
                    "20230605090000_FE-204-PSO-CAM-1.png": "c73838c7c73838c7",
                    "20230605100000_FE-204-PSO-CAM-1.png": "c73838c7c73838c7",
                    "20230605110000_FE-204-PSO-CAM-1.png": "c73938c6c0e7c738",
                    "20230605120000_FE-204-PSO-CAM-1.png": "c4c437673839c6f8",
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
                "20230605080000_FE-204-PSO-CAM-1.zip",
                None,
                {
                    "20230605080000_FE-204-PSO-CAM-1.png": "da2d4927045f24bf",
                },
                id="Zip export of single channel to test filename",
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
        TestExport.compile_get_params(get_params, "lower_level", lower_level)
        TestExport.compile_get_params(get_params, "upper_level", upper_level)
        TestExport.compile_get_params(get_params, "colourmap_name", colourmap_name)

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
                if filename_in_zip.endswith(".csv"):
                    # there should be a file in the test dir that the contents of the
                    # CSV in the zip file need comparing to
                    assert_text_file_contents(
                        filepath_or_hash,
                        zip_file.open(filename_in_zip).read().decode(),
                    )
                else:
                    # this is an image so it needs a perceptual hash generating and
                    # comparing with what is expected
                    image = Image.open(zip_file.open(filename_in_zip))
                    assert filepath_or_hash == str(imagehash.phash(image))
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
