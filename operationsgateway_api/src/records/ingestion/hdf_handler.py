from datetime import datetime
import logging
from tempfile import SpooledTemporaryFile
from typing import List, Tuple

import h5py
from pydantic import ValidationError

from operationsgateway_api.src.constants import DATA_DATETIME_FORMAT, ID_DATETIME_FORMAT
from operationsgateway_api.src.exceptions import HDFDataExtractionError, ModelError
from operationsgateway_api.src.models import (
    ImageChannelMetadataModel,
    ImageChannelModel,
    ImageModel,
    RecordMetadataModel,
    RecordModel,
    ScalarChannelMetadataModel,
    ScalarChannelModel,
    WaveformChannelMetadataModel,
    WaveformChannelModel,
    WaveformModel,
)
from operationsgateway_api.src.records.image import Image
from operationsgateway_api.src.records.ingestion.channel_checks import ChannelChecks
from operationsgateway_api.src.records.waveform import Waveform


log = logging.getLogger()


class HDFDataHandler:
    def __init__(self, hdf_temp_file: SpooledTemporaryFile) -> None:
        """
        Convert a HDF file that comes attached in a HTTP request (not in HDF format)
        into a HDF file via h5py
        """
        self.hdf_file = h5py.File(hdf_temp_file, "r")
        self.channels = {}
        self.waveforms = []
        self.images = []

    async def extract_data(
        self,
    ) -> Tuple[RecordModel, List[WaveformModel], List[ImageModel]]:
        """
        Extract data from a HDF file that is formatted in the OperationsGateway data
        structure format. Metadata of the shot, channel data and its metadata is
        extracted
        """
        log.debug("Extracting data from HDF files")

        metadata_hdf = dict(self.hdf_file.attrs)
        timestamp_format = "%Y-%m-%dT%H:%M:%S%z"
        try:
            metadata_hdf["timestamp"] = datetime.strptime(
                metadata_hdf["timestamp"],
                timestamp_format,
            )
        except ValueError:
            # Try using alternative timestamp format that might be used for older HDF
            # files such as old Gemini test data
            # TODO - when Gemini test data is no longer needed, remove this try/except
            # block that attempts to convert the timestamp for a second time. Go
            # straight to raising the exception instead
            try:
                metadata_hdf["timestamp"] = datetime.strptime(
                    metadata_hdf["timestamp"],
                    DATA_DATETIME_FORMAT,
                )
            except ValueError as exc:
                raise HDFDataExtractionError(
                    "Incorrect timestamp format for metadata timestamp. Use"
                    f" {timestamp_format} instead",
                ) from exc

        self.record_id = metadata_hdf["timestamp"].strftime(ID_DATETIME_FORMAT)
        await self.extract_channels()

        try:
            record = RecordModel(
                _id=self.record_id,
                metadata=RecordMetadataModel(**metadata_hdf),
                channels=self.channels,
            )
        except ValidationError as exc:
            raise ModelError(str(exc)) from exc

        return record, self.waveforms, self.images, self.internal_failed_channel

    def _unexpected_attribute(self, channel_type, value):
        """
        tells the location it is called whether to stop. Stops if the value for data
        is not the same what it is meant to be for the channel type
        using the self.acceptable_datasets dictionary
        """
        return any(val != self.acceptable_datasets[channel_type][0] for val in value)

    def _extract_image(
        self,
        internal_failed_channel,
        channel_name,
        channel_metadata,
        value,
    ):
        """
        Extract data for images in the HDF file and place the data into
        relevant Pydantic models as well as performing on image specific checks
        """
        image_path = Image.get_relative_path(self.record_id, channel_name)

        if self._unexpected_attribute("image", value):
            internal_failed_channel.append(
                {channel_name: "unexpected group or dataset in channel group"},
            )
            return None, internal_failed_channel

        try:
            self.images.append(
                ImageModel(path=image_path, data=value["data"][()]),
            )

            channel = ImageChannelModel(
                metadata=ImageChannelMetadataModel(**channel_metadata),
                image_path=image_path,
            )
            return channel, False
        except KeyError:
            internal_failed_channel.append(
                {channel_name: "data attribute is missing"},
            )
            return None, internal_failed_channel
        except ValidationError as exc:
            raise ModelError(str(exc)) from exc

    def _extract_scalar(
        self,
        internal_failed_channel,
        channel_name,
        channel_metadata,
        value,
    ):
        """
        Extract data for scalars in the HDF file and place the data into
        relevant Pydantic models as well as performing on scalar specific checks
        """
        if self._unexpected_attribute("scalar", value):
            internal_failed_channel.append(
                {channel_name: "unexpected group or dataset in channel group"},
            )
            return None, internal_failed_channel

        try:
            channel = ScalarChannelModel(
                metadata=ScalarChannelMetadataModel(**channel_metadata),
                data=value["data"][()],
            )
            return channel, False
        except KeyError:
            internal_failed_channel.append(
                {channel_name: "data attribute is missing"},
            )
            return None, internal_failed_channel
        except ValidationError as exc:
            for error in exc.errors():
                if (
                    error["type"] == "int_type"
                    or error["type"] == "float_type"
                    or error["type"] == "string_type"
                ):
                    internal_failed_channel.append(
                        {channel_name: "data has wrong datatype"},
                    )
                    break
                else:
                    raise ModelError(str(exc)) from exc
            return None, internal_failed_channel

    def _extract_waveform(
        self,
        internal_failed_channel,
        channel_name,
        channel_metadata,
        value,
    ):
        """
        Extract data for waveforms in the HDF file and place the data into
        relevant Pydantic models as well as performing on waveform specific checks
        """
        waveform_id = f"{self.record_id}_{channel_name}"
        waveform_path = Waveform.get_relative_path(self.record_id, channel_name)
        log.debug("Waveform ID: %s", waveform_id)

        value_list = []
        for val in value:
            value_list.append(val)
        if (list(set(value_list) - set(self.acceptable_datasets["waveform"]))) != []:
            internal_failed_channel.append(
                {channel_name: "unexpected group or dataset in channel group"},
            )
            return None, internal_failed_channel

        try:
            channel = WaveformChannelModel(
                metadata=WaveformChannelMetadataModel(**channel_metadata),
                waveform_path=waveform_path,
            )

            self.waveforms.append(
                WaveformModel(
                    path=waveform_path,
                    x=value["x"][()],
                    y=value["y"][()],
                ),
            )

            return channel, False
        except KeyError:
            for key in ["x", "y"]:
                try:
                    value[key]
                except KeyError:
                    internal_failed_channel.append(
                        {channel_name: f"{key} attribute is missing"},
                    )
            return None, internal_failed_channel
        except ValidationError as exc:
            raise ModelError(str(exc)) from exc

    async def extract_channels(self) -> None:
        """
        Extract data from each data channel in the HDF file and place the data into
        relevant Pydantic models
        """

        internal_failed_channel = []
        # TODO - move this into a ClassVar on the models? or move into init at least
        self.acceptable_datasets = {
            "scalar": ["data"],
            "image": ["data"],
            "waveform": ["x", "y"],
        }

        for channel_name, value in self.hdf_file.items():
            channel_metadata = dict(value.attrs)

            channel_checks = ChannelChecks(
                ingested_record={channel_name: channel_metadata},
            )
            log.debug("Pre channel find")
            await channel_checks.set_manifest_channels()
            log.debug("Post channel find")
            response = await channel_checks.channel_dtype_checks()
            if response != []:
                internal_failed_channel.extend(response)
                continue

            if value.attrs["channel_dtype"] == "image":
                channel, fail = self._extract_image(
                    internal_failed_channel,
                    channel_name,
                    channel_metadata,
                    value,
                )
                if fail:
                    internal_failed_channel = fail
                    continue

            elif value.attrs["channel_dtype"] == "rgb-image":
                # TODO - implement colour image ingestion. Currently waiting on the
                # OG-HDF5 converter to support conversion of colour images.
                # Implementation will be as per greyscale image (`get_relative_path()`
                # then append to `self.images`) but might require extracting a different
                # part of the value
                raise HDFDataExtractionError("Colour images cannot be ingested")
            elif value.attrs["channel_dtype"] == "scalar":
                channel, fail = self._extract_scalar(
                    internal_failed_channel,
                    channel_name,
                    channel_metadata,
                    value,
                )
                if fail:
                    internal_failed_channel = fail
                    continue

            elif value.attrs["channel_dtype"] == "waveform":
                channel, fail = self._extract_waveform(
                    internal_failed_channel,
                    channel_name,
                    channel_metadata,
                    value,
                )
                if fail:
                    internal_failed_channel = fail
                    continue

            # Put channels into a dictionary to give a good structure to query them in
            # the database
            self.channels[channel_name] = channel
        self.internal_failed_channel = internal_failed_channel
