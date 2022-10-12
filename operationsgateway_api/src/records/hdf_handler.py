from datetime import datetime
import logging
from tempfile import SpooledTemporaryFile

import h5py
from pydantic import ValidationError

from operationsgateway_api.src.exceptions import HDFDataExtractionError, ModelError
from operationsgateway_api.src.models import (
    Image,
    ImageChannel,
    ImageChannelMetadata,
    Record,
    RecordMetadata,
    ScalarChannel,
    ScalarChannelMetadata,
    Waveform,
    WaveformChannel,
    WaveformChannelMetadata,
)
from operationsgateway_api.src.records.image import Image as ImageClass


log = logging.getLogger()


class HDFDataHandler:
    def __init__(self, hdf_temp_file: SpooledTemporaryFile):
        """
        Convert a HDF file that comes attached in a HTTP request (not in HDF format)
        into a HDF file via h5py
        """
        self.hdf_file = h5py.File(hdf_temp_file, "r")
        self.channels = {}
        self.waveforms = []
        self.images = []

    def extract_data(self):
        """
        Extract data from a HDF file that is formatted in the OperationsGateway data
        structure format. Metadata of the shot, channel data and its metadata is
        extracted. The data is then returned in a dictionary
        """

        metadata_hdf = dict(self.hdf_file.attrs)
        try:
            # TODO 1 - make sure that we can round-trip timestamps
            metadata_hdf["timestamp"] = datetime.strptime(
                metadata_hdf["timestamp"],
                "%Y-%m-%d %H:%M:%S",
            )
            self.record_id = metadata_hdf["timestamp"].strftime("%Y%m%d%H%M%S")
        except ValueError as exc:
            raise HDFDataExtractionError(
                "Incorrect timestamp format for metadata timestamp. Use %Y-%m-%d"
                " %H:%M:%S",
            ) from exc

        self.extract_channels()

        try:
            record = Record(
                _id=self.record_id,
                metadata=RecordMetadata(**metadata_hdf),
                channels=self.channels,
            )
        except ValidationError as exc:
            raise ModelError(str(exc))

        return record, self.waveforms, self.images

    def extract_channels(self):
        for channel_name, value in self.hdf_file.items():
            channel_metadata = dict(value.attrs)

            if value.attrs["channel_dtype"] == "image":
                image_path = ImageClass.get_image_path(
                    self.record_id,
                    channel_name,
                    full_path=False,
                )

                try:
                    self.images.append(Image(path=image_path, data=value["data"][()]))

                    channel = ImageChannel(
                        metadata=ImageChannelMetadata(**channel_metadata),
                        image_path=image_path,
                    )
                except ValidationError as exc:
                    raise ModelError(str(exc))
            elif value.attrs["channel_dtype"] == "rgb-image":
                # TODO - implement colour image ingestion. Currently waiting on the
                # OG-HDF5 converter to support conversion of colour images.
                # Implementation will be as per greyscale image (`get_image_path()`
                # then append to `self.images`) but might require extracting a different
                # part of the value
                raise HDFDataExtractionError("Colour images cannot be ingested")
            elif value.attrs["channel_dtype"] == "scalar":
                try:
                    channel = ScalarChannel(
                        metadata=ScalarChannelMetadata(**channel_metadata),
                        data=value["data"][()],
                    )
                except ValidationError as exc:
                    raise ModelError(str(exc))
            elif value.attrs["channel_dtype"] == "waveform":
                waveform_id = f"{self.record_id}_{channel_name}"
                log.debug("Waveform ID: %s", waveform_id)

                try:
                    channel = WaveformChannel(
                        metadata=WaveformChannelMetadata(**channel_metadata),
                        waveform_id=waveform_id,
                    )

                    self.waveforms.append(
                        Waveform(
                            _id=waveform_id,
                            x=value["x"][()],
                            y=value["y"][()],
                        ),
                    )
                except ValidationError as exc:
                    raise ModelError(str(exc))

            # Put channels into a dictionary to give a good structure to query them in
            # the database
            self.channels[channel_name] = channel
