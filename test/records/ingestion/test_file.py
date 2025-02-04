import pytest

from operationsgateway_api.src.exceptions import RejectFileError
from operationsgateway_api.src.records.ingestion.file_checks import FileChecks
from test.records.ingestion.create_test_hdf import create_test_hdf_file


class TestFile:
    @pytest.mark.asyncio
    async def test_file_checks_pass(self, remove_hdf_file):
        record_data, _, _, _ = await create_test_hdf_file()
        file_checker = FileChecks(record_data)

        file_checker.epac_data_version_checks()

    @pytest.mark.asyncio
    async def test_minor_version_too_high(self, remove_hdf_file):
        record_data, _, _, _ = await create_test_hdf_file(
            data_version=["1.4", "exists"],
        )
        file_checker = FileChecks(record_data)

        assert (
            file_checker.epac_data_version_checks()
            == "File minor version number too high (expected <=1)"
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
        record_data, _, _, _ = await create_test_hdf_file(data_version=data_version)
        file_checker = FileChecks(record_data)

        with pytest.raises(RejectFileError, match=match):
            file_checker.epac_data_version_checks()
