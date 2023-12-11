import logging

import numpy as np

from operationsgateway_api.src.channels.channel_manifest import ChannelManifest
from operationsgateway_api.src.exceptions import RejectFileError, RejectRecordError
from operationsgateway_api.src.models import (
    ImageChannelMetadataModel,
    RecordModel,
    ScalarChannelMetadataModel,
    WaveformChannelMetadataModel,
)


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
        ):  # is the has attribute needed?
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
        ):  # is the has attribute needed?
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
        ):  # is the has attribute needed?
            if type(ingested_metadata.active_experiment) != str:
                raise RejectRecordError(
                    "active_experiment has wrong datatype. Expected string",
                )
        if (
            hasattr(ingested_metadata, "shotnum")
            and ingested_metadata.shotnum is not None
        ):  # is the has attribute needed?
            if type(ingested_metadata.shotnum) != int:
                raise RejectRecordError("shotnum has wrong datatype. Expected integer")


class ChannelChecks:
    def __init__(self, ingested_record: RecordModel, ingested_waveform, ingested_image):
        self.ingested_record = ingested_record
        self.ingested_waveform = ingested_waveform
        self.ingested_image = ingested_image

    async def channel_dtype_checks(self):
        ingested_channels = (self.ingested_record).channels
        manifest_channels = (await get_manifest())["channels"]

        supported_values = [
            "scalar",
            "image",
            "rgb-image",
            "waveform",
        ]

        rejected_channels = []

        for key, value in ingested_channels.items():
            if hasattr(value.metadata, "channel_dtype"):
                if (
                    manifest_channels[key]["type"] != value.metadata.channel_dtype
                    or value.metadata.channel_dtype not in supported_values
                ):
                    rejected_channels.append(
                        {
                            key: "channel_dtype has wrong data type "
                            "or its value is unsupported",
                        },
                    )
            else:
                rejected_channels.append({key: "channel_dtype attribute is missing"})
        return rejected_channels

    def required_attribute_checks(self):
        ingested_channels = (self.ingested_record).channels
        ingested_waveform = self.ingested_waveform
        ingested_image = self.ingested_image

        rejected_channels = []
        for key, value in ingested_channels.items():
            if value.metadata.channel_dtype == "scalar":
                if hasattr(value, "metadata"):
                    if not isinstance(value.metadata, ScalarChannelMetadataModel):
                        rejected_channels.append({key: "metadata has wrong datatype"})
                else:
                    rejected_channels.append({key: "metadata attribute is missing"})

                if hasattr(value, "data"):
                    pass
                else:
                    rejected_channels.append({key: "data attribute is missing"})

            if value.metadata.channel_dtype == "image":
                if hasattr(value, "metadata"):
                    if not isinstance(value.metadata, ImageChannelMetadataModel):
                        rejected_channels.append({key: "metadata has wrong datatype"})
                else:
                    rejected_channels.append({key: "metadata attribute is missing"})

                if hasattr(value, "image_path"):
                    path_to_check = value.image_path
                    if type(path_to_check) == str:
                        images = 0

                        matching_image = None

                        for image in ingested_image:
                            if image.path == path_to_check:
                                matching_image = image
                                images += 1

                        if (
                            matching_image
                            and hasattr(matching_image, "data")
                            and isinstance(matching_image.data, np.ndarray)
                        ):
                            pass
                        else:
                            if matching_image:
                                rejected_channels.append(
                                    {key: "data has wrong datatype, should be ndarray"},
                                )
                            elif images > 1:
                                rejected_channels.append(
                                    {
                                        key: "more than one matching path attribute "
                                        "detected, must be mutually exclusive",
                                    },
                                )
                            else:
                                rejected_channels.append(
                                    {
                                        key: "path attribute is missing or is "
                                        "wrong data type for this image_path",
                                    },
                                )
                    else:
                        rejected_channels.append(
                            {
                                key: "image_path attribute wrong datatype, "
                                "should be string",
                            },
                        )
                else:
                    rejected_channels.append({key: "image_path attribute is missing"})

            if value.metadata.channel_dtype == "waveform":
                if hasattr(value, "metadata"):
                    if not isinstance(value.metadata, WaveformChannelMetadataModel):
                        rejected_channels.append({key: "metadata has wrong datatype"})
                else:
                    rejected_channels.append({key: "metadata attribute is missing"})

                if hasattr(value, "waveform_id"):
                    id_to_check = value.waveform_id
                    if type(id_to_check) == str:
                        waveforms = 0

                        matching_waveform = None

                        for waveform in ingested_waveform:
                            if waveform.id_ == id_to_check:
                                matching_waveform = waveform
                                waveforms += 1
                        if (
                            matching_waveform
                            and hasattr(matching_waveform, "x")
                            and hasattr(matching_waveform, "y")
                            and isinstance(matching_waveform.x, list)
                            and isinstance(matching_waveform.y, list)
                            and all(
                                isinstance(element, float)
                                for element in matching_waveform.x
                            )
                            and all(
                                isinstance(element, float)
                                for element in matching_waveform.y
                            )
                        ):
                            pass
                        else:
                            if matching_waveform:
                                rejected_channels.append(
                                    {
                                        key: "x or y has wrong datatype, "
                                        "should be a list of floats",
                                    },
                                )
                            elif waveforms > 1:
                                rejected_channels.append(
                                    {
                                        key: "more than one matching id attribute "
                                        "detected, must be mutually exclusive",
                                    },
                                )
                            else:
                                rejected_channels.append(
                                    {
                                        key: "id_ attribute is missing or is wrong "
                                        "data type for this waveform_id",
                                    },
                                )
                    else:
                        rejected_channels.append(
                            {
                                key: "waveform_id attribute wrong datatype, "
                                "should be string",
                            },
                        )
                else:
                    rejected_channels.append({key: "waveform_id attribute is missing"})
        return rejected_channels

    def optional_dtype_checks(self):
        ingested_channels = (self.ingested_record).channels
        rejected_channels = []

        for key, value in ingested_channels.items():
            if value.metadata.channel_dtype == "scalar":
                if hasattr(value.metadata, "units") and (
                    type(value.metadata.units) != str
                    and value.metadata.units is not None
                ):
                    rejected_channels.append(
                        {key: "units attribute has wrong datatype"},
                    )

            if value.metadata.channel_dtype == "image":
                if hasattr(value.metadata, "exposure_time_s") and (
                    type(value.metadata.exposure_time_s) != float
                    and value.metadata.exposure_time_s is not None
                ):
                    rejected_channels.append(
                        {key: "exposure_time_s attribute has wrong datatype"},
                    )
                if hasattr(value.metadata, "gain") and (
                    type(value.metadata.gain) != float
                    and value.metadata.gain is not None
                ):
                    rejected_channels.append({key: "gain attribute has wrong datatype"})
                if hasattr(value.metadata, "x_pixel_size") and (
                    type(value.metadata.x_pixel_size) != float
                    and value.metadata.x_pixel_size is not None
                ):
                    rejected_channels.append(
                        {key: "x_pixel_size attribute has wrong datatype"},
                    )
                if hasattr(value.metadata, "x_pixel_units") and (
                    type(value.metadata.x_pixel_units) != str
                    and value.metadata.x_pixel_units is not None
                ):
                    rejected_channels.append(
                        {key: "x_pixel_units attribute has wrong datatype"},
                    )
                if hasattr(value.metadata, "y_pixel_size") and (
                    type(value.metadata.y_pixel_size) != float
                    and value.metadata.y_pixel_size is not None
                ):
                    rejected_channels.append(
                        {key: "y_pixel_size attribute has wrong datatype"},
                    )
                if hasattr(value.metadata, "y_pixel_units") and (
                    type(value.metadata.y_pixel_units) != str
                    and value.metadata.y_pixel_units is not None
                ):
                    rejected_channels.append(
                        {key: "y_pixel_units attribute has wrong datatype"},
                    )

                if hasattr(value, "thumbnail") and (
                    type(value.thumbnail) != str and value.thumbnail is not None
                ):
                    rejected_channels.append(
                        {key: "thumbnail attribute has wrong datatype"},
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

                if hasattr(value, "thumbnail") and (
                    type(value.thumbnail) != str and value.thumbnail is not None
                ):
                    rejected_channels.append(
                        {key: "thumbnail attribute has wrong datatype"},
                    )

        return rejected_channels

    def dataset_checks(self):
        ingested_channels = (self.ingested_record).channels
        ingested_waveform = self.ingested_waveform
        ingested_image = self.ingested_image

        rejected_channels = []

        for key, value in ingested_channels.items():
            if value.metadata.channel_dtype == "scalar":
                if (
                    type(value.data) != int
                    and type(value.data) != float
                    and type(value.data) != str
                ):
                    rejected_channels.append({key: "data attribute has wrong datatype"})

            if value.metadata.channel_dtype == "image":

                path_to_check = value.image_path
                matching_image = None

                for image in ingested_image:
                    if image.path == path_to_check:
                        matching_image = image

                data = matching_image.data

                if isinstance(data, np.ndarray) and (
                    data.dtype == np.uint16 or data.dtype == np.uint8
                ):
                    if all(isinstance(element, np.ndarray) for element in data):
                        if all(
                            isinstance(inner_list, data.dtype.type)
                            for inner_list in data.flat
                        ):
                            pass
                        else:
                            rejected_channels.append(
                                {key: "data attribute has wrong shape"},
                            )
                    else:
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
                id_to_check = value.waveform_id
                matching_waveform = None

                for waveform in ingested_waveform:
                    if waveform.id_ == id_to_check:
                        matching_waveform = waveform

                x = matching_waveform.x
                y = matching_waveform.y

                if type(x) != list:
                    rejected_channels.append({key: "x attribute has wrong shape"})
                if type(y) != list:
                    rejected_channels.append({key: "y attribute has wrong shape"})

                if all(isinstance(element, float) for element in x):
                    pass
                else:
                    rejected_channels.append(
                        {
                            key: "x attribute has wrong datatype, should "
                            "be a list of floats",
                        },
                    )

                if all(isinstance(element, float) for element in y):
                    pass
                else:
                    rejected_channels.append(
                        {
                            key: "y attribute has wrong datatype, should be a "
                            "list of floats",
                        },
                    )

        return rejected_channels

    def unrecognised_attribute_checks(self):
        ingested_channels = (self.ingested_record).channels
        ingested_waveform = self.ingested_waveform
        ingested_image = self.ingested_image

        scalar_values = [
            "metadata",
            "data",
        ]
        scalar_metadata = [
            "channel_dtype",
            "units",
        ]

        image_values = [
            "metadata",
            "image_path",
            "thumbnail",
        ]
        image_metadata = [
            "channel_dtype",
            "exposure_time_s",
            "gain",
            "x_pixel_size",
            "y_pixel_size",
            "x_pixel_units",
            "y_pixel_units",
        ]
        image_data = [
            "path",
            "data",
        ]

        waveform_values = [
            "metadata",
            "thumbnail",
            "waveform_id",
        ]
        waveform_metadata = [
            "channel_dtype",
            "x_units",
            "y_units",
        ]
        waveform_data = [
            "id_",
            "x",
            "y",
        ]

        rejected_channels = []

        for key, value in ingested_channels.items():
            if value.metadata.channel_dtype == "scalar":

                value_keys = value.dict().keys()
                unexpected_value_keys = set(value_keys) - set(scalar_values)

                if unexpected_value_keys:
                    rejected_channels.append(
                        {key: "unknown attribute in scalar channel"},
                    )

                metadata_keys = value.metadata.dict().keys()
                unexpected_metadata_keys = set(metadata_keys) - set(scalar_metadata)

                if unexpected_metadata_keys:
                    rejected_channels.append(
                        {key: "unknown attribute in scalar metadata"},
                    )

            if value.metadata.channel_dtype == "image":
                path_to_check = value.image_path
                matching_image = None

                for image in ingested_image:
                    if image.path == path_to_check:
                        matching_image = image

                value_keys = value.dict().keys()
                unexpected_value_keys = set(value_keys) - set(image_values)

                metadata_keys = value.metadata.dict().keys()
                unexpected_metadata_keys = set(metadata_keys) - set(image_metadata)

                image_keys = matching_image.dict().keys()
                unexpected_image_keys = set(image_keys) - set(image_data)

                if unexpected_value_keys:
                    rejected_channels.append(
                        {key: "unknown attribute in image channel"},
                    )

                if unexpected_metadata_keys:
                    rejected_channels.append(
                        {key: "unknown attribute in image metadata"},
                    )

                if unexpected_image_keys:
                    rejected_channels.append({key: "unknown attribute in image data"})

            if value.metadata.channel_dtype == "waveform":
                id_to_check = value.waveform_id
                matching_waveform = None

                for waveform in ingested_waveform:
                    if waveform.id_ == id_to_check:
                        matching_waveform = waveform

                value_keys = value.dict().keys()
                unexpected_value_keys = set(value_keys) - set(waveform_values)

                metadata_keys = value.metadata.dict().keys()
                unexpected_metadata_keys = set(metadata_keys) - set(waveform_metadata)

                waveform_keys = matching_waveform.dict().keys()
                unexpected_waveform_keys = set(waveform_keys) - set(waveform_data)

                if unexpected_value_keys:
                    rejected_channels.append(
                        {key: "unknown attribute in waveform channel"},
                    )

                if unexpected_metadata_keys:
                    rejected_channels.append(
                        {key: "unknown attribute in waveform metadata"},
                    )

                if unexpected_waveform_keys:
                    rejected_channels.append(
                        {key: "unknown attribute in waveform data"},
                    )

        return rejected_channels

    async def channel_name_check(self):

        ingested_channels = (self.ingested_record).channels
        manifest = (await get_manifest())["channels"]

        rejected_channels = []

        for key in list(ingested_channels.keys()):
            if key not in manifest:
                rejected_channels.append(
                    {
                        key: "Channel name is not recognised (does not appear "
                        "in manifest)",
                    },
                )
                # reject on import?
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
                    rejected_channels[key].extend(reasons)

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
    # checked in certain circumstances
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
            raise RejectRecordError("timestamp is matches, other metadata does not")

        elif (
            shot_match
            and not time_match
            and not epac_match
            and not area_match
            and not experiment_match
        ):
            raise RejectRecordError("shotnum is matches, other metadata does not")

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
