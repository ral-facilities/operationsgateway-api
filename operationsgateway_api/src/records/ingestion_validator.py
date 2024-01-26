import logging

import numpy as np

from operationsgateway_api.src.channels.channel_manifest import ChannelManifest
from operationsgateway_api.src.exceptions import RejectFileError, RejectRecordError
from operationsgateway_api.src.models import RecordModel


log = logging.getLogger()


async def get_manifest():
    return await ChannelManifest.get_most_recent_manifest()


class FileChecks:
    def __init__(self, ingested_record: RecordModel):
        self.ingested_record = ingested_record

    def epac_data_version_checks(self):
        ingested_metadata = (self.ingested_record).metadata
        if (
            hasattr(ingested_metadata, "epac_ops_data_version")
            and ingested_metadata.epac_ops_data_version is not None
        ):
            epac_number = ingested_metadata.epac_ops_data_version
            if type(ingested_metadata.epac_ops_data_version) != str:
                raise RejectFileError(
                    "epac_ops_data_version has wrong datatype. Should be string",
                )
            else:
                epac_numbers = epac_number.split(".")
                if epac_numbers[0] != "1":
                    raise RejectFileError(
                        "epac_ops_data_version major version was not 1",
                    )
                if int(epac_numbers[1]) > 0:
                    return "File minor version number too high (expected 0)"
        else:
            raise RejectFileError("epac_ops_data_version does not exist")
        # a RecordMetadataModel is already returned when
        # epac_ops_data_version does not exist


class RecordChecks:
    def __init__(self, ingested_record: RecordModel):
        self.ingested_record = ingested_record

    def active_area_checks(self):
        ingested_metadata = (self.ingested_record).metadata
        if (
            hasattr(ingested_metadata, "active_area")
            and ingested_metadata.active_area is not None
        ):
            if type(ingested_metadata.active_area) != str:
                raise RejectRecordError(
                    "active_area has wrong datatype. Expected string",
                )
        else:
            raise RejectRecordError("active_area is missing")

    def optional_metadata_checks(self):
        ingested_metadata = (self.ingested_record).metadata
        if (
            hasattr(ingested_metadata, "active_experiment")
            and ingested_metadata.active_experiment is not None
        ):
            if type(ingested_metadata.active_experiment) != str:
                raise RejectRecordError(
                    "active_experiment has wrong datatype. Expected string",
                )
        if (
            hasattr(ingested_metadata, "shotnum")
            and ingested_metadata.shotnum is not None
        ):
            if type(ingested_metadata.shotnum) != int:
                raise RejectRecordError("shotnum has wrong datatype. Expected integer")


class ChannelChecks:
    def __init__(
        self,
        ingested_record=None,
        ingested_waveform=None,
        ingested_image=None,
        internal_failed_channel=None,
    ):
        self.ingested_record = ingested_record or []
        self.ingested_waveform = ingested_waveform or []
        self.ingested_image = ingested_image or []
        self.internal_failed_channel = internal_failed_channel or []

    def _merge_internal_failed(
        self,
        rejected_channels,
        internal_failed_channel,
        accept_list,
    ):
        if internal_failed_channel != []:
            for response in internal_failed_channel:
                for _key, reason in response.items():
                    for accepted_reason in accept_list:
                        if reason == accepted_reason:
                            rejected_channels.append(response)
        return rejected_channels

    async def channel_dtype_checks(self):
        ingested_channels = self.ingested_record
        dump = False
        if type(ingested_channels) != dict:
            ingested_channels = ingested_channels.channels
            dump = True

        manifest_channels = (await get_manifest())["channels"]

        supported_values = [
            "scalar",
            "image",
            "rgb-image",
            "waveform",
        ]

        rejected_channels = []

        for key, value in ingested_channels.items():
            if dump:
                value = value.metadata.model_dump()

            response = await self.channel_name_check(key)
            if response != []:
                rejected_channels.extend(response)
                continue

            if "channel_dtype" in value:
                if (
                    manifest_channels[key]["type"] != value["channel_dtype"]
                    or value["channel_dtype"] not in supported_values
                ):
                    rejected_channels.append(
                        {
                            key: "channel_dtype has wrong data type "
                            "or its value is unsupported",
                        },
                    )
            else:
                rejected_channels.append(
                    {
                        key: "channel_dtype attribute is missing"
                        " (cannot perform other checks without)",
                    },
                )

        rejected_channels = self._merge_internal_failed(
            rejected_channels,
            self.internal_failed_channel,
            [
                "channel_dtype attribute is missing (cannot perform "
                "other checks without)",
                "channel_dtype has wrong data type or its value is unsupported",
            ],
        )

        return rejected_channels

    def required_attribute_checks(self):
        ingested_channels = (self.ingested_record).channels
        ingested_waveform = self.ingested_waveform
        ingested_image = self.ingested_image

        rejected_channels = []
        for key, value in ingested_channels.items():
            if value.metadata.channel_dtype == "image":
                image = None
                for images in ingested_image:
                    if images.path == value.image_path:
                        image = images
                        continue

                if not isinstance(image.data, np.ndarray):
                    rejected_channels.append(
                        {key: "data attribute has wrong datatype, should be ndarray"},
                    )

            if value.metadata.channel_dtype == "waveform":
                matching_waveform = None
                for waveform in ingested_waveform:
                    if waveform.id_ == value.waveform_id:
                        matching_waveform = waveform
                        continue

                if not isinstance(matching_waveform.x, list) or not all(
                    isinstance(element, float) for element in matching_waveform.x
                ):
                    rejected_channels.append(
                        {key: "x attribute must be a list of floats"},
                    )

                if not isinstance(matching_waveform.y, list) or not all(
                    isinstance(element, float) for element in matching_waveform.y
                ):
                    rejected_channels.append(
                        {key: "y attribute must be a list of floats"},
                    )

        rejected_channels = self._merge_internal_failed(
            rejected_channels,
            self.internal_failed_channel,
            [
                "data attribute is missing",
                "data has wrong datatype",
                "x attribute is missing",
                "y attribute is missing",
                "channel_dtype attribute is missing (cannot perform "
                "other checks without)",
                "channel_dtype has wrong data type or its value is unsupported",
            ],
        )

        return rejected_channels

    @classmethod
    def scalar_metadata_checks(cls, key, value_dict, rejected_channels):

        if type(value_dict) != dict:
            value_dict = value_dict.model_dump()

        if ("units" in value_dict) and (
            type(value_dict["units"]) != str and value_dict["units"] is not None
        ):
            rejected_channels.append(
                {key: "units attribute has wrong datatype"},
            )
        return rejected_channels

    @classmethod
    def image_metadata_checks(cls, key, value_dict, rejected_channels):

        if type(value_dict) != dict:
            value_dict = value_dict.model_dump()

        if ("exposure_time_s" in value_dict) and (
            not isinstance(value_dict["exposure_time_s"], (float, np.floating))
            and value_dict["exposure_time_s"] is not None
        ):
            rejected_channels.append(
                {key: "exposure_time_s attribute has wrong datatype"},
            )
        if ("gain" in value_dict) and (
            not isinstance(value_dict["gain"], (float, np.floating))
            and value_dict["gain"] is not None
        ):
            rejected_channels.append({key: "gain attribute has wrong datatype"})
        if ("x_pixel_size" in value_dict) and (
            not isinstance(value_dict["x_pixel_size"], (float, np.floating))
            and value_dict["x_pixel_size"] is not None
        ):
            rejected_channels.append(
                {key: "x_pixel_size attribute has wrong datatype"},
            )
        if ("x_pixel_units" in value_dict) and (
            type(value_dict["x_pixel_units"]) != str
            and value_dict["x_pixel_units"] is not None
        ):
            rejected_channels.append(
                {key: "x_pixel_units attribute has wrong datatype"},
            )
        if ("y_pixel_size" in value_dict) and (
            not isinstance(value_dict["y_pixel_size"], (float, np.floating))
            and value_dict["y_pixel_size"] is not None
        ):
            rejected_channels.append(
                {key: "y_pixel_size attribute has wrong datatype"},
            )
        if ("y_pixel_units" in value_dict) and (
            type(value_dict["y_pixel_units"]) != str
            and value_dict["y_pixel_units"] is not None
        ):
            rejected_channels.append(
                {key: "y_pixel_units attribute has wrong datatype"},
            )
        return rejected_channels

    def optional_dtype_checks(self):
        ingested_channels = (self.ingested_record).channels
        rejected_channels = []

        for key, value in ingested_channels.items():
            if value.metadata.channel_dtype == "scalar":

                rejected_channels = self.scalar_metadata_checks(
                    key,
                    value.metadata,
                    rejected_channels,
                )

            if value.metadata.channel_dtype == "image":
                rejected_channels = self.image_metadata_checks(
                    key,
                    value.metadata,
                    rejected_channels,
                )

            if value.metadata.channel_dtype == "waveform":
                if hasattr(value.metadata, "x_units") and (
                    type(value.metadata.x_units) != str
                    and value.metadata.x_units is not None
                ):
                    rejected_channels.append(
                        {key: "x_units attribute has wrong datatype"},
                    )
                if hasattr(value.metadata, "y_units") and (
                    type(value.metadata.y_units) != str
                    and value.metadata.y_units is not None
                ):
                    rejected_channels.append(
                        {key: "y_units attribute has wrong datatype"},
                    )

        return rejected_channels

    def _waveform_dataset_check(self, rejected_channels, value, key, letter):
        if type(value) != list:
            rejected_channels.append({key: letter + " attribute has wrong shape"})
        else:
            if not all(isinstance(element, float) for element in value):
                rejected_channels.append(
                    {
                        key: letter + " attribute has wrong datatype, should "
                        "be a list of floats",
                    },
                )
        return rejected_channels

    def dataset_checks(self):
        ingested_channels = (self.ingested_record).channels
        ingested_waveform = self.ingested_waveform
        ingested_image = self.ingested_image

        rejected_channels = []

        for key, value in ingested_channels.items():
            if value.metadata.channel_dtype == "image":
                data = None
                for image in ingested_image:
                    if image.path == value.image_path:
                        data = image.data
                        continue

                if isinstance(data, np.ndarray) and (
                    data.dtype == np.uint16 or data.dtype == np.uint8
                ):
                    if not all(isinstance(element, np.ndarray) for element in data):
                        rejected_channels.append(
                            {key: "data attribute has wrong shape"},
                        )
                else:
                    rejected_channels.append(
                        {
                            key: "data attribute has wrong datatype, "
                            "should be uint16 or uint8",
                        },
                    )

            if value.metadata.channel_dtype == "waveform":
                matching_waveform = None

                for waveform in ingested_waveform:
                    if waveform.id_ == value.waveform_id:
                        matching_waveform = waveform
                        continue

                x = matching_waveform.x
                y = matching_waveform.y

                rejected_channels = self._waveform_dataset_check(
                    rejected_channels,
                    x,
                    key,
                    "x",
                )
                rejected_channels = self._waveform_dataset_check(
                    rejected_channels,
                    y,
                    key,
                    "y",
                )

        rejected_channels = self._merge_internal_failed(
            rejected_channels,
            self.internal_failed_channel,
            [
                "data attribute is missing",
                "data has wrong datatype",
                "x attribute is missing",
                "y attribute is missing",
                "channel_dtype attribute is missing (cannot perform "
                "other checks without)",
                "channel_dtype has wrong data type or its value is unsupported",
            ],
        )

        return rejected_channels

    def unrecognised_attribute_checks(self):

        rejected_channels = []

        rejected_channels = self._merge_internal_failed(
            rejected_channels,
            self.internal_failed_channel,
            [
                "unexpected group or dataset in channel group",
            ],
        )

        return rejected_channels

    def _check_name(self, rejected_channels, manifest, key):
        if key not in manifest:
            rejected_channels.append(
                {
                    key: "Channel name is not recognised (does not appear "
                    "in manifest)",
                },
            )
        return rejected_channels

    async def channel_name_check(self, mode="direct"):
        manifest = (await get_manifest())["channels"]

        rejected_channels = []

        if mode != "direct":
            rejected_channels = self._check_name(rejected_channels, manifest, mode)
            return rejected_channels

        ingested_channels = (self.ingested_record).channels

        for key in list(ingested_channels.keys()):
            rejected_channels = self._check_name(rejected_channels, manifest, key)

        rejected_channels = self._merge_internal_failed(
            rejected_channels,
            self.internal_failed_channel,
            [
                "Channel name is not recognised (does not appear in manifest)",
            ],
        )

        return rejected_channels

    def _organise_dict(self, list_of_dicts):
        organised_dict = {}

        for d in list_of_dicts:
            for key, reason in d.items():
                if key not in organised_dict:
                    organised_dict[key] = [reason]
                else:
                    organised_dict[key].append(reason)
        return organised_dict

    async def channel_checks(self):
        ingested_channels = (self.ingested_record).channels

        dtype_response = self._organise_dict(await self.channel_dtype_checks())
        attribute_response = self._organise_dict(self.required_attribute_checks())
        optional_response = self._organise_dict(self.optional_dtype_checks())
        dataset_response = self._organise_dict(self.dataset_checks())
        unrecognised_response = self._organise_dict(
            self.unrecognised_attribute_checks(),
        )
        channel_name_response = self._organise_dict(await self.channel_name_check())

        response_list = [
            dtype_response,
            attribute_response,
            optional_response,
            dataset_response,
            unrecognised_response,
            channel_name_response,
        ]

        rejected_channels = {}

        for d in response_list:
            for key, reasons in d.items():
                if key not in rejected_channels:
                    rejected_channels[key] = reasons
                else:
                    for reason in reasons:
                        if reason not in rejected_channels[key]:
                            rejected_channels[key].append(reason)

        channel_list = ingested_channels.keys()

        keys_to_remove = rejected_channels.keys()

        accepted_channels = [
            channel for channel in channel_list if channel not in keys_to_remove
        ]

        channel_response = {
            "accepted channels": accepted_channels,
            "rejected channels": rejected_channels,
        }

        return channel_response


class PartialImportChecks:
    def __init__(self, ingested_record: RecordModel, stored_record: RecordModel):
        self.ingested_record = ingested_record
        self.stored_record = stored_record

    def metadata_checks(self):
        ingested_metadata = (self.ingested_record).metadata
        stored_metadata = (self.stored_record).metadata

        time_match = ingested_metadata.timestamp == stored_metadata.timestamp
        epac_match = (
            ingested_metadata.epac_ops_data_version
            == stored_metadata.epac_ops_data_version
        )
        shot_match = ingested_metadata.shotnum == stored_metadata.shotnum
        area_match = ingested_metadata.active_area == stored_metadata.active_area
        experiment_match = (
            ingested_metadata.active_experiment == stored_metadata.active_experiment
        )

        if ingested_metadata == stored_metadata:
            log.info("record metadata matches existing record perfectly")
            return "accept record and merge"

        elif (
            time_match
            and not epac_match
            and not shot_match
            and not area_match
            and not experiment_match
        ):
            raise RejectRecordError("timestamp matches, other metadata does not")

        elif (
            shot_match
            and not time_match
            and not epac_match
            and not area_match
            and not experiment_match
        ):
            raise RejectRecordError("shotnum matches, other metadata does not")

        elif not time_match and not shot_match:
            return "accept as a new record"

    def channel_checks(self):
        ingested_channels = (self.ingested_record).channels
        stored_channels = (self.stored_record).channels

        rejected_channels = {}
        accepted_channels = []

        for key in list(ingested_channels.keys()):
            if key in stored_channels:
                rejected_channels[key] = "Channel is already present in existing record"
            else:
                accepted_channels.append(key)

        channel_response = {
            "accepted channels": accepted_channels,
            "rejected channels": rejected_channels,
        }

        return channel_response
