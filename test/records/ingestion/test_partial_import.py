import copy
from unittest.mock import patch

import pytest

from operationsgateway_api.src.exceptions import RejectRecordError
from operationsgateway_api.src.records.ingestion.partial_import_checks import (
    PartialImportChecks,
)
from test.records.ingestion.create_test_hdf import create_test_hdf_file


CHANNEL_PRESENT_MESSAGE = "Channel is already present in existing record"


class TestPartialImport:
    @pytest.mark.parametrize(
        "test_type, response",
        [
            pytest.param(
                "match",
                "accept_merge",
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
                "accept_new",
                id="Neither shotnum nor timestamp matches",
            ),
            pytest.param(
                "single",
                "inconsistent metadata",
                id="Shotnum does not match",
            ),
        ],
    )
    @pytest.mark.asyncio
    async def test_metadata_checks(self, remove_hdf_file, test_type, response):

        hdf_tuple = await create_test_hdf_file()

        stored_record = copy.deepcopy(hdf_tuple[0])

        if test_type == "time":
            # alter so only time matches
            stored_record.metadata.epac_ops_data_version = "2.3"
            stored_record.metadata.shotnum = 234
            stored_record.metadata.active_area = "ae2"
            stored_record.metadata.active_experiment = "4898"
        elif test_type == "num":
            # alter so only num matches
            stored_record.metadata.epac_ops_data_version = "2.3"
            stored_record.metadata.timestamp = "3122-04-07 14:28:16"
            stored_record.metadata.active_area = "ae2"
            stored_record.metadata.active_experiment = "4898"
        elif test_type == "neither":
            # alter so neither shotnum nor timestamp matches
            stored_record.metadata.timestamp = "3122-04-07 14:28:16"
            stored_record.metadata.shotnum = 234
        elif test_type == "single":
            # alter so only shotnum is wrong
            stored_record.metadata.shotnum = 234

        partial_import_checker = PartialImportChecks(hdf_tuple[0], stored_record)

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
