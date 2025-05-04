import copy
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient
import pytest

from operationsgateway_api.src.exceptions import HDFDataExtractionError
from operationsgateway_api.src.records.ingestion.partial_import_checks import (
    PartialImportChecks,
)
from test.endpoints.conftest import reset_record_storage
from test.records.ingestion.create_test_hdf import create_test_hdf_file


CHANNEL_PRESENT_MESSAGE = "Channel is already present in existing record"


class TestPartialImport:
    """
    These tests, and their associated implementation, came from the need
    to have the shotnumber be unique in the system.
    More history at: https://stfc.atlassian.net/browse/DSEGOG-412
    Test cases: https://github.com/ral-facilities/operationsgateway-api/pull/179
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
    async def test_no_timestamp_no_shotnum(
        self,
        test_app,
        reset_record_storage,
        login_and_get_token,
    ):
        """
        Test 2: No timestamp, no shot number.Should raise error in
        create_test_hdf_file due to missing required timestamp metadata.
        """
        with pytest.raises(HDFDataExtractionError, match="Invalid timestamp metadata"):
            await create_test_hdf_file(
                timestamp=["", "missing"],
                shotnum=["", "missing"],
            )

    @pytest.mark.asyncio
    async def test_no_timestamp_new_shotnum(
        self,
        test_app,
        reset_record_storage,
        login_and_get_token,
    ):
        """
        Test 3: No timestamp, New shot number. Should raise error in
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
    async def test_no_timestamp_existing_shotnum(
        self,
        test_app,
        reset_record_storage,
        login_and_get_token,
    ):
        """
        Test 4: No timestamp, but with a shotnumber that already exists in the
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

    @pytest.mark.asyncio
    async def test_new_timestamp_new_shotnum(
        self,
        test_app,
        reset_record_storage,
        login_and_get_token,
    ):
        """
        Test 5: New timestamp, new shot number. Should be accepted as both are unique.
        """
        # Create a file with the default time stamp (20200407142816)
        # and the default shot number (366272)
        await create_test_hdf_file()
        response = self._submit_hdf(test_app, login_and_get_token)
        assert response.status_code == 201
        assert "added as 20200407142816" in response.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_new_timestamp_existing_shotnum(
        self,
        test_app,
        reset_record_storage,
        login_and_get_token,
    ):
        """
        Test 6: new timestamp, existing shot number.Should be rejected (400)
        because shot number needs to be unique in the system.
        """
        # Create a file with the default time stamp (20200407142816)
        # and the default shot number (366272)
        await create_test_hdf_file()
        self._submit_hdf(test_app, login_and_get_token)

        # Create a file with a new time stamp but the same default shot number (366272)
        timestamp_now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        await create_test_hdf_file(timestamp=[timestamp_now, "exists"])

        response = self._submit_hdf(test_app, login_and_get_token)
        assert response.status_code == 400
        assert (
            "a record with this shotnum already exists"
            in response.json()["detail"].lower()
        )

    @pytest.mark.asyncio
    async def test_existing_timestamp_no_shotnum(
        self,
        test_app,
        reset_record_storage,
        login_and_get_token,
    ):
        """
        Test 7: Existing timestamp (present in the db), no shot number.
        Should be updated (200) due to duplicate timestamp and shotnum being optional.
        """
        # Create a file with the default time stamp (20200407142816)
        # with a missing shot number
        await create_test_hdf_file(shotnum=["", "missing"])
        self._submit_hdf(test_app, login_and_get_token)
        # Submit again with same timestamp in the file
        response = self._submit_hdf(test_app, login_and_get_token)
        print(response.text)
        assert response.status_code == 200
        assert "updated 20200407142816" in response.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_existing_timestamp_new_shotnum(
        self,
        test_app,
        reset_record_storage,
        login_and_get_token,
    ):
        """
        Test 8: Existing timestamp, new shot number. Should be rejected (400)
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
    async def test_existing_timestamp_none_shotnum(
        self,
        test_app,
        reset_record_storage,
        login_and_get_token,
    ):
        """
        Test 9: Existing timestamp, None as shot number. Should be rejected (400)
        because of inconsistent metadata. The shot number doesn't match the
        shot number in the db
        """
        # Create a file with the default time stamp (20200407142816)
        # and the default shot number (366272)
        await create_test_hdf_file()
        self._submit_hdf(test_app, login_and_get_token)

        # Create a file with the same time stamp above but a different shot number
        await create_test_hdf_file(shotnum=["9999", "missing"])

        response = self._submit_hdf(test_app, login_and_get_token)
        assert response.status_code == 400
        assert "inconsistent metadata" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_existing_timestamp_existing_shotnum(
        self,
        test_app,
        reset_record_storage,
        login_and_get_token,
    ):
        """
        Test 10: existing timestamp, existing shot number. Both the timestamp
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
    async def test_existing_version_with_different_version(
        self,
        test_app,
        reset_record_storage,
        login_and_get_token,
    ):
        """
        Test 11: Both the timestamp and the shot number exist in the system.
        All other metadata match apart from the version, which shouldn't be
        checked for. Should be accepted as a merge (200).
        """
        # Create a file with the default time stamp (20200407142816),
        # default shot number (366272), and the default version (1.0)
        await create_test_hdf_file()
        self._submit_hdf(test_app, login_and_get_token)

        # create the same file again but with a different version,
        # the value has to be present as it's a required field but the api
        # should NOT reject if they are different
        await create_test_hdf_file(data_version=["1.2", "exists"])
        response = self._submit_hdf(test_app, login_and_get_token)
        assert response.status_code == 200
        assert "updated 20200407142816" in response.json()["message"].lower()

        # make sure the version hasn't been updated and remains the standard
        response = test_app.get(
            "/records/20200407142816",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )
        assert response.status_code == 200
        assert response.json()["metadata"]["epac_ops_data_version"] == "1.0"

    @pytest.mark.parametrize(
        "test_type, response",
        [
            pytest.param(
                "all",
                {
                    "accepted_channels": [],
                    "rejected_channels": {
                        "CM-202-CVC-WFS": CHANNEL_PRESENT_MESSAGE,
                        "CM-202-CVC-WFS-COEF": CHANNEL_PRESENT_MESSAGE,
                        "PM-201-FE-EM": CHANNEL_PRESENT_MESSAGE,
                        "PM-201-FE-CAM-2-CENX": CHANNEL_PRESENT_MESSAGE,
                        "PM-201-FE-CAM-2-FWHMX": CHANNEL_PRESENT_MESSAGE,
                        "PM-201-FE-CAM-2-CENY": CHANNEL_PRESENT_MESSAGE,
                        "PM-201-FE-CAM-2-FWHMY": CHANNEL_PRESENT_MESSAGE,
                        "PM-201-PA1-EM": CHANNEL_PRESENT_MESSAGE,
                        "PM-201-FE-CAM-1": CHANNEL_PRESENT_MESSAGE,
                        "PM-201-PA2-EM": CHANNEL_PRESENT_MESSAGE,
                        "PM-201-TJ-EM": CHANNEL_PRESENT_MESSAGE,
                        "PM-201-TJ-CAM-2-CENX": CHANNEL_PRESENT_MESSAGE,
                        "PM-201-FE-CAM-2": CHANNEL_PRESENT_MESSAGE,
                        "PM-201-HJ-PD": CHANNEL_PRESENT_MESSAGE,
                        "PM-201-TJ-CAM-2-FWHMX": CHANNEL_PRESENT_MESSAGE,
                        "PM-201-TJ-CAM-2-CENY": CHANNEL_PRESENT_MESSAGE,
                        "PM-201-TJ-CAM-2-FWHMY": CHANNEL_PRESENT_MESSAGE,
                    },
                },
                id="All channels match",
            ),
            pytest.param(
                "some",
                {
                    "accepted_channels": [
                        "PM-201-FE-EM",
                        "PM-201-TJ-CAM-2-CENX",
                        "PM-201-TJ-CAM-2-FWHMY",
                    ],
                    "rejected_channels": {
                        "CM-202-CVC-WFS": CHANNEL_PRESENT_MESSAGE,
                        "CM-202-CVC-WFS-COEF": CHANNEL_PRESENT_MESSAGE,
                        "PM-201-FE-CAM-2-CENX": CHANNEL_PRESENT_MESSAGE,
                        "PM-201-FE-CAM-2-FWHMX": CHANNEL_PRESENT_MESSAGE,
                        "PM-201-FE-CAM-2-CENY": CHANNEL_PRESENT_MESSAGE,
                        "PM-201-FE-CAM-2-FWHMY": CHANNEL_PRESENT_MESSAGE,
                        "PM-201-PA1-EM": CHANNEL_PRESENT_MESSAGE,
                        "PM-201-FE-CAM-1": CHANNEL_PRESENT_MESSAGE,
                        "PM-201-PA2-EM": CHANNEL_PRESENT_MESSAGE,
                        "PM-201-TJ-EM": CHANNEL_PRESENT_MESSAGE,
                        "PM-201-FE-CAM-2": CHANNEL_PRESENT_MESSAGE,
                        "PM-201-HJ-PD": CHANNEL_PRESENT_MESSAGE,
                        "PM-201-TJ-CAM-2-FWHMX": CHANNEL_PRESENT_MESSAGE,
                        "PM-201-TJ-CAM-2-CENY": CHANNEL_PRESENT_MESSAGE,
                    },
                },
                id="Some channels match",
            ),
            pytest.param(
                "none",
                {
                    "accepted_channels": [
                        "CM-202-CVC-WFS",
                        "CM-202-CVC-WFS-COEF",
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
                    "rejected_channels": {},
                },
                id="No channels match",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_import_channel_checks(self, remove_hdf_file, test_type, response):

        hdf_tuple = await create_test_hdf_file()
        stored_record = copy.deepcopy(hdf_tuple[0])

        if test_type == "some":
            channels = stored_record.channels
            # alter so only some match
            channels["GEM"] = channels.pop("PM-201-FE-EM")
            channels["COMP"] = channels.pop("PM-201-TJ-CAM-2-CENX")
            channels["TYP"] = channels.pop("PM-201-TJ-CAM-2-FWHMY")
        elif test_type == "none":
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
            channels["p"] = channels.pop("CM-202-CVC-WFS")
            channels["q"] = channels.pop("CM-202-CVC-WFS-COEF")

        partial_import_checker = PartialImportChecks(hdf_tuple[0], stored_record)

        # This test doesn't use any data stored in the database/Echo, it provides
        # instances of RecordModel as inputs to PartialImportChecks. For image and
        # waveform channels, a check is conducted to make sure the associated
        # image/waveform is actually on Echo and because we're not using stored data for
        # this test, we need to mock that check
        with patch.object(partial_import_checker.echo, "head_object") as mock_is_stored:
            mock_is_stored.return_value = True
            partial_import_channel_checks = partial_import_checker.channel_checks(
                {"rejected_channels": {}},
            )

        assert partial_import_channel_checks == response
