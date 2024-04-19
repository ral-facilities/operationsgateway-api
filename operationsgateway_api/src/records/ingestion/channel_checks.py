import logging

import numpy as np


log = logging.getLogger()


class ChannelChecks:
    def __init__(
        self,
        ingested_record=None,
        ingested_waveform=None,
        ingested_image=None,
        internal_failed_channel=None,
    ):
        """
        This class is instantiated using everything from hdf_handler
        internal_failed_channel is a list of channels that have failed inside
        hdf_handler already
        """
        self.ingested_record = ingested_record or []
        self.ingested_waveform = ingested_waveform or []
        self.ingested_image = ingested_image or []
        self.internal_failed_channel = internal_failed_channel or []

        self.supported_channel_types = [
            "scalar",
            "image",
            "rgb-image",
            "waveform",
        ]

    def set_channels(self, manifest) -> None:
        self.manifest_channels = manifest["channels"]

    def _merge_internal_failed(
        self,
        rejected_channels,
        internal_failed_channel,
        accept_list,
    ):
        """
        Merges internal_failed_channel with rejected_channels from the main code
        it merges them based on the reason for failing so if there is a duplicate
        reason then it is ignored in the merge

        only merges reasons that are in the accept_list to separate between checks
        """
        if internal_failed_channel != []:
            for response in internal_failed_channel:
                for reason in response.values():
                    for accepted_reason in accept_list:
                        if reason == accepted_reason:
                            rejected_channels.append(response)
        return rejected_channels

    async def channel_dtype_checks(self):
        """
        Checks if the channel_dtype of each channel exists and has the correct datatype
        and is one of the supported values

        if they aren't they are added to the rejected_channels list as a dict along with
        the reason they failed to return to the used as an output dict
        """
        ingested_channels = self.ingested_record
        dump = False
        if type(ingested_channels) != dict:
            ingested_channels = ingested_channels.channels
            dump = True

        rejected_channels = []

        for key, value in ingested_channels.items():
            if dump:
                value = value.metadata.model_dump()

            response = await self.channel_name_check(key)
            if response != []:
                rejected_channels.extend(response)
                log.debug(
                    "Channel name not recognised, further checks on '%s' won't be run",
                    key,
                )
                continue

            if "channel_dtype" in value:
                if (
                    self.manifest_channels[key]["type"] != value["channel_dtype"]
                    or value["channel_dtype"] not in self.supported_channel_types
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
                        key: "channel_dtype attribute is missing",
                    },
                )

        rejected_channels = self._merge_internal_failed(
            rejected_channels,
            self.internal_failed_channel,
            [
                "channel_dtype attribute is missing",
                "channel_dtype has wrong data type or its value is unsupported",
            ],
        )

        return rejected_channels

    def required_attribute_checks(self):
        """
        Checks if the required attributes of each channel exists and has the
        correct datatype

        if they don't they are added to the rejected_channels list as a dict along with
        the reason they failed to return to the used as an output dict
        """
        ingested_channels = self.ingested_record.channels
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
                    if waveform.path == value.waveform_path:
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
                "channel_dtype attribute is missing",
                "channel_dtype has wrong data type or its value is unsupported",
            ],
        )

        return rejected_channels

    @classmethod
    def scalar_metadata_checks(cls, key, value_dict, rejected_channels):
        """
        Various checks brought out of the main function to simplify it

        when called it returns a list of rejected_channels (if any) from the checks ran
        """

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
        """
        Various checks brought out of the main function to simplify it

        when called it returns a list of rejected_channels (if any) from the checks ran
        """

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
        """
        Checks if the optional attributes of each channel has the correct datatype
        calls two other functions that return any failed channels. done to simplify
        this function

        if they don't they are added to the rejected_channels list as a dict along with
        the reason they failed to return to the used as an output dict
        """
        ingested_channels = self.ingested_record.channels
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
        """
        Is ran to differentiate between the datasets "x" and "y" for waveforms

        this generates a rejected channel message depending on what was fed to this
        function (which dataset and why it failed)
        """
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
        """
        Checks if the datasets of each channel exists and have the correct datatype

        if they don't they are added to the rejected_channels list as a dict along with
        the reason they failed to return to the used as an output dict
        """
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
                    if waveform.path == value.waveform_path:
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
                "channel_dtype attribute is missing",
                "channel_dtype has wrong data type or its value is unsupported",
            ],
        )

        return rejected_channels

    def unrecognised_attribute_checks(self):
        """
        All this does is merges the failed channels from hdf_handler into
        rejected_channels as this check is ran inside hdf_handler

        only merging any channel with "unexpected group or dataset in channel group"
        as a fail message
        """

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
        """
        Checks if the channel name appears in the most recent channel manifest

        if it doesn't it is added to rejected_channels
        """
        if key not in manifest:
            log.debug("Channel '%s' is not in manifest", key)
            rejected_channels.append(
                {
                    key: "Channel name is not recognised (does not appear "
                    "in manifest)",
                },
            )
        return rejected_channels

    async def channel_name_check(self, mode="direct"):
        """
        This is ran inside the hdf_handler because otherwise non-existant channels cause
        it to fail

        it can also be ran directly from anywhere else (hence the mode)

        Checks if the channel name appears in the most recent channel manifest
        if it doesn't it is added to rejected_channels
        """

        rejected_channels = []

        if mode != "direct":
            rejected_channels = self._check_name(
                rejected_channels,
                self.manifest_channels,
                mode,
            )
            return rejected_channels

        ingested_channels = (self.ingested_record).channels

        for key in list(ingested_channels.keys()):
            rejected_channels = self._check_name(
                rejected_channels,
                self.manifest_channels,
                key,
            )

        rejected_channels = self._merge_internal_failed(
            rejected_channels,
            self.internal_failed_channel,
            [
                "Channel name is not recognised (does not appear in manifest)",
            ],
        )

        return rejected_channels

    def _organise_dict(self, list_of_dicts):
        """
        Gets list_of_dicts

        gets each key and separates them
        if any key was duplicated originally, the reasons are merged into a list under
        one key
        """
        organised_dict = {}

        for d in list_of_dicts:
            for key, reason in d.items():
                if key not in organised_dict:
                    organised_dict[key] = [reason]
                else:
                    organised_dict[key].append(reason)
        return organised_dict

    async def channel_checks(self):
        """
        Runs each channel check
        merges all failed channels into one list of dicts with no duplicated keys

        returns a dictionary of a list of accepted channels and a dictionary of rejected
        channels (with no duplicate keys and a list of fail reasons for each key)
        """
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
            "accepted_channels": accepted_channels,
            "rejected_channels": rejected_channels,
        }

        return channel_response
