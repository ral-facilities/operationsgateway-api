import pytest

from operationsgateway_api.src.exceptions import (
    AuthServerError,
    ChannelManifestError,
    HDFDataExtractionError,
    RecordError,
)


class TestExceptionCodes:
    def test_auth_server_error(self):
        with pytest.raises(AuthServerError) as exc_info:
            raise AuthServerError("AuthServerError pytest")

        assert exc_info.value.status_code == 500

    def test_hdf_data_extraction_error(self):
        with pytest.raises(HDFDataExtractionError) as exc_info:
            raise HDFDataExtractionError("HDFDataExtractionError pytest")

        assert exc_info.value.status_code == 400

    def test_channel_manifest_error(self):
        with pytest.raises(ChannelManifestError) as exc_info:
            raise ChannelManifestError("ChannelManifestError pytest")

        assert exc_info.value.status_code == 400

    def test_record_error(self):
        with pytest.raises(RecordError) as exc_info:
            raise RecordError("RecordError pytest")

        assert exc_info.value.status_code == 500
