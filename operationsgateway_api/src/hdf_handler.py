from datetime import datetime
import logging
from tempfile import SpooledTemporaryFile

import h5py
from pydantic import ValidationError

from operationsgateway_api.src.models import (
    Image,
    ImageChannel,
    ImageChannelMetadata,
    RecordMetadata,
    RecordM,
    ScalarChannel,
    ScalarChannelMetadata,
    Waveform,
    WaveformChannel,
    WaveformChannelMetadata,
)
from operationsgateway_api.src.records.image import Image as ImageClass


log = logging.getLogger()


# TODO - put class into `records/`
class HDFDataHandler:
    def __init__(self, hdf_temp_file: SpooledTemporaryFile):
        """
        Convert a HDF file that comes attached in a HTTP request (not in HDF format)
        into a HDF file via h5py
        """
        self.hdf_file = h5py.File(hdf_temp_file, "r")


    def extract_data(self):
        """
        Extract data from a HDF file that is formatted in the OperationsGateway data
        structure format. Metadata of the shot, channel data and its metadata is
        extracted. The data is then returned in a dictionary
        """

        metadata_hdf = dict(self.hdf_file.attrs)
        try:
            # TODO - make sure that we can round-trip timestamps
            metadata_hdf["timestamp"] = datetime.strptime(
                metadata_hdf["timestamp"], "%Y-%m-%d %H:%M:%S",
            )
            self.record_id = metadata_hdf["timestamp"].strftime("%Y%m%d%H%M%S")
        except ValueError as e:
            # TODO - add proper exception
            print(f"DATE CONVERSION BROKE: {e}")

        channels = {}
        waveforms = []
        images = []

        for channel_name, value in self.hdf_file.items():
            channel_metadata = dict(value.attrs)

            if value.attrs["channel_dtype"] == "image":
                image_path = ImageClass.get_image_path(
                    self.record_id, channel_name, full_path=False,
                )
                images.append(Image(path=image_path, data=value["data"][()]))

                try:
                    channel = ImageChannel(
                        metadata=ImageChannelMetadata(**channel_metadata),
                        image_path=image_path,
                    )
                except ValidationError as e:
                    # TODO - add proper exception
                    print(f"IMAGE CHANNEL BROKE: {e}")
            elif value.attrs["channel_dtype"] == "rgb-image":
                # TODO - when we don't want random noise anymore, we could probably
                # combine this code with greyscale images, its the same implementation
                image_path = ImageClass.get_image_path(
                    self.record_id, channel_name, full_path=False,
                )

                # TODO - refactor this branch
                """
                # Gives random noise, where only example RGB I have sends full black
                # image. Comment out to store true data
                image_data = np.random.randint(
                    0,
                    255,
                    size=(300, 400, 3),
                    dtype=np.uint8,
                )

                images[image_path] = image_data

                record["channels"][channel_name] = {
                    "metadata": {},
                    "image_path": image_path,
                }
                """
            elif value.attrs["channel_dtype"] == "scalar":
                try:
                    channel = ScalarChannel(
                        metadata=ScalarChannelMetadata(**channel_metadata),
                        data=value["data"][()],
                    )
                except ValidationError as e:
                    # TODO - add exception
                    print(f"SCALAR CHANNEL BROKE: {e}")
            elif value.attrs["channel_dtype"] == "waveform":
                waveform_id = f"{self.record_id}_{channel_name}"
                log.debug("Waveform ID: %s", waveform_id)

                try:
                    channel = WaveformChannel(
                        metadata=WaveformChannelMetadata(**channel_metadata),
                        waveform_id=waveform_id,
                    )

                    waveforms.append(
                        Waveform(
                            _id=waveform_id,
                            x=value["x"][()],
                            y=value["y"][()],
                        )
                    )
                except ValidationError as e:
                    # TODO - add exception
                    print(f"WAVEFORM CHANNEL BROKE: {e}")

            # Put channels into a dictionary to give a good structure to query them in
            # the database
            channels[channel_name] = channel

        try:
            record = RecordM(
                _id=self.record_id,
                metadata=RecordMetadata(**metadata_hdf),
                channels=channels,
            )
        except ValidationError as e:
            print(f"RECORD CREATION BROKE: {e}")

        # TODO - put these in self?
        return record, waveforms, images
