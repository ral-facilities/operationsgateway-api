from fastapi.testclient import TestClient
import pytest

from operationsgateway_api.src.exceptions import HDFDataExtractionError
from test.endpoints.conftest import reset_record_storage
from test.records.ingestion.create_test_hdf import create_test_hdf_file


class TestIngestionValidationRules:
    """
    These tests, and their associated implementation, came from the need
    to have the shotnumber be unique in the system.
    More history at: https://stfc.atlassian.net/browse/DSEGOG-412
    """

    def _submit_hdf(self, test_app, token) -> TestClient:
        with open("test.h5", "rb") as f:
            files = {"file": ("test.h5", f)}
            return test_app.post(
                "/submit/hdf",
                headers={"Authorization": f"Bearer {token}"},
                files=files,
            )

    @pytest.mark.asyncio
    async def test_new_timestamp_no_shotnum(
        self,
        test_app,
        reset_record_storage,
        login_and_get_token,
    ):
        """
        Test 1: New timestamp, no shot number. Should be accepted (201)
        because shot number is optional.
        """
        # Create a file with the default time stamp (20200407142816),
        # with a missing shot number
        await create_test_hdf_file(shotnum=["", "missing"])
        response = self._submit_hdf(test_app, login_and_get_token)
        assert response.status_code == 201
        assert "added as 20200407142816" in response.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_existing_timestamp_no_shotnum(
        self,
        test_app,
        reset_record_storage,
        login_and_get_token,
    ):
        """
        Test 2: Existing timestamp (present in the db), no shot number.
        Should be updated (200) due to duplicate timestamp.
        """
        # Create a file with the default time stamp (20200407142816)
        # with a missing shot number
        await create_test_hdf_file(shotnum=["", "missing"])
        self._submit_hdf(test_app, login_and_get_token)

        # Submit again with same timestamp in the file
        response = self._submit_hdf(test_app, login_and_get_token)
        assert response.status_code == 200
        assert "updated 20200407142816" in response.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_no_timestamp_no_shotnum(
        self,
        test_app,
        reset_record_storage,
        login_and_get_token,
    ):
        """
        Test 3: No timestamp, no shot number.Should raise error in
        create_test_hdf_file due to missing required timestamp metadata.
        """
        with pytest.raises(HDFDataExtractionError, match="Invalid timestamp metadata"):
            await create_test_hdf_file(
                timestamp=["", "missing"],
                shotnum=["", "missing"],
            )

    @pytest.mark.asyncio
    async def test_new_timestamp_new_shotnum(
        self,
        test_app,
        reset_record_storage,
        login_and_get_token,
    ):
        """
        Test 4: New timestamp, new shot number. Should be accepted as both are unique.
        """
        # Create a file with the default time stamp (20200407142816)
        # and the default shot number (366272)
        await create_test_hdf_file()
        response = self._submit_hdf(test_app, login_and_get_token)
        assert response.status_code == 201
        assert "added as 20200407142816" in response.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_existing_timestamp_new_shotnum(
        self,
        test_app,
        reset_record_storage,
        login_and_get_token,
    ):
        """
        Test 5: Existing timestamp, new shot number. Should be rejected (400)
        because of inconsistent metadata. The shot number doesn't match the
        shot number in the db
        """
        # Create a file with the default time stamp (20200407142816)
        # and the default shot number (366272)
        await create_test_hdf_file()
        self._submit_hdf(test_app, login_and_get_token)

        # Create a file with the same time stamp above but a different shot number
        await create_test_hdf_file(shotnum=["9999", "exists"])

        response = self._submit_hdf(test_app, login_and_get_token)
        assert response.status_code == 400
        assert "inconsistent metadata" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_no_timestamp_new_shotnum(
        self,
        test_app,
        reset_record_storage,
        login_and_get_token,
    ):
        """
        Test 6: No timestamp, New shot number. Should raise error in
        create_test_hdf_file due to missing required timestamp metadata.
        """
        with pytest.raises(HDFDataExtractionError, match="Invalid timestamp metadata"):
            # Create a file with a missing time stamp, but with the
            # default shot number (366272) that doesn't exist on the system
            await create_test_hdf_file(
                timestamp=["", "missing"],
                shotnum=["10101", "exists"],
            )

    @pytest.mark.asyncio
    async def test_new_timestamp_existing_shotnum(
        self,
        test_app,
        reset_record_storage,
        login_and_get_token,
    ):
        """
        Test 7: new timestamp, existing shot number.Should be rejected (400)
        because shot number needs to be unique in the system.
        """
        # Create a file with the default time stamp (20200407142816)
        # and the default shot number (366272)
        await create_test_hdf_file()
        self._submit_hdf(test_app, login_and_get_token)

        # Create a file with a new time stamp but the same default shot number (366272)
        await create_test_hdf_file(timestamp=["2025-04-07T14:28:16+00:00", "exists"])

        response = self._submit_hdf(test_app, login_and_get_token)
        assert response.status_code == 400
        assert "shot number already exists" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_existing_timestamp_existing_shotnum(
        self,
        test_app,
        reset_record_storage,
        login_and_get_token,
    ):
        """
        Test 8: existing timestamp, existing shot number. Both the timestamp
        and the shot number exist in the system. Should be accepted as a merge (200).
        """
        # Create a file with the default time stamp (20200407142816)
        # and the default shot number (366272)
        await create_test_hdf_file()
        self._submit_hdf(test_app, login_and_get_token)

        # submit the same file again
        response = self._submit_hdf(test_app, login_and_get_token)
        assert response.status_code == 200
        assert "updated 20200407142816" in response.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_no_timestamp_existing_shotnum(
        self,
        test_app,
        reset_record_storage,
        login_and_get_token,
    ):
        """
        Test 9: No timestamp, but with a shotnumber that already exists in the
        system. Should raise error in create_test_hdf_file due to missing
        required timestamp metadata.
        """
        # Create a file with the default time stamp (20200407142816)
        # and the default shot number (366272)
        await create_test_hdf_file()
        self._submit_hdf(test_app, login_and_get_token)

        with pytest.raises(HDFDataExtractionError, match="Invalid timestamp metadata"):
            # Create a file with a missing timestamp field
            # but with the same shot number as above (366272)
            await create_test_hdf_file(timestamp=["", "missing"])
