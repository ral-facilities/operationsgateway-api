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

    def extract_data(self) -> Tuple[RecordModel, List[WaveformModel], List[ImageModel]]:
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
        self.extract_channels()

        try:
            record = RecordModel(
                _id=self.record_id,
                metadata=RecordMetadataModel(**metadata_hdf),
                channels=self.channels,
            )
        except ValidationError as exc:
            raise ModelError(str(exc)) from exc

        return record, self.waveforms, self.images, self.channel_dtype_missing

    def extract_channels(self) -> None:
        """
        Extract data from each data channel in the HDF file and place the data into
        relevant Pydantic models
        """
        
        channel_dtype_missing = []
        
        for channel_name, value in self.hdf_file.items():
            channel_metadata = dict(value.attrs)
            
            try:
                value.attrs["channel_dtype"]
            except KeyError:
                channel_dtype_missing.append(channel_name)
                continue

            if value.attrs["channel_dtype"] == "image":
                image_path = Image.get_image_path(self.record_id, channel_name)

                try:
                    self.images.append(
                        ImageModel(path=image_path, data=value["data"][()]),
                    )

                    channel = ImageChannelModel(
                        metadata=ImageChannelMetadataModel(**channel_metadata),
                        image_path=image_path,
                    )
                except ValidationError as exc:
                    raise ModelError(str(exc)) from exc
            elif value.attrs["channel_dtype"] == "rgb-image":
                # TODO - implement colour image ingestion. Currently waiting on the
                # OG-HDF5 converter to support conversion of colour images.
                # Implementation will be as per greyscale image (`get_image_path()`
                # then append to `self.images`) but might require extracting a different
                # part of the value
                raise HDFDataExtractionError("Colour images cannot be ingested")
            elif value.attrs["channel_dtype"] == "scalar":
                try:
                    channel = ScalarChannelModel(
                        metadata=ScalarChannelMetadataModel(**channel_metadata),
                        data=value["data"][()],
                    )
                except ValidationError as exc:
                    raise ModelError(str(exc)) from exc
            elif value.attrs["channel_dtype"] == "waveform":
                waveform_id = f"{self.record_id}_{channel_name}"
                log.debug("Waveform ID: %s", waveform_id)

                try:
                    channel = WaveformChannelModel(
                        metadata=WaveformChannelMetadataModel(**channel_metadata),
                        waveform_id=waveform_id,
                    )

                    self.waveforms.append(
                        WaveformModel(
                            _id=waveform_id,
                            x=value["x"][()],
                            y=value["y"][()],
                        ),
                    )
                except ValidationError as exc:
                    raise ModelError(str(exc)) from exc

            # Put channels into a dictionary to give a good structure to query them in
            # the database
            self.channels[channel_name] = channel
            self.channel_dtype_missing = channel_dtype_missing
