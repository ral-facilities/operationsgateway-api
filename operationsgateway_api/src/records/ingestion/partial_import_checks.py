import logging

from operationsgateway_api.src.exceptions import EchoS3Error, RejectRecordError
from operationsgateway_api.src.models import (
    ImageChannelModel,
    RecordModel,
    WaveformChannelModel,
)
from operationsgateway_api.src.records.echo_interface import EchoInterface
from operationsgateway_api.src.records.image import Image
from operationsgateway_api.src.records.waveform import Waveform


log = logging.getLogger()


class PartialImportChecks:
    def __init__(self, ingested_record: RecordModel, stored_record: RecordModel):
        """
        This class is instantiated using the record_data form a current stored record
        and from an incoming record using hdf_handler
        """
        self.ingested_record = ingested_record
        self.stored_record = stored_record
        self.echo = EchoInterface()

    def metadata_checks(self):
        """
        Compares the metadata of both files and decides what to do from there

        it can:
            accept as a new record
            merge the record
            reject the record
        """
        ingested_metadata = self.ingested_record.metadata
        stored_metadata = self.stored_record.metadata

        try:
            time_match = (ingested_metadata.timestamp).replace(
                tzinfo=None,
            ) == stored_metadata.timestamp
        except Exception:
            time_match = (ingested_metadata.timestamp) == stored_metadata.timestamp

        epac_match = (
            ingested_metadata.epac_ops_data_version
            == stored_metadata.epac_ops_data_version
        )
        shot_match = ingested_metadata.shotnum == stored_metadata.shotnum
        area_match = ingested_metadata.active_area == stored_metadata.active_area
        experiment_match = (
            ingested_metadata.active_experiment == stored_metadata.active_experiment
        )

        if time_match and epac_match and shot_match and area_match and experiment_match:
            log.info("record metadata matches existing record perfectly")
            return "accept_merge"

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
            return "accept_new"

        else:
            log.error(
                "Metadata for file being ingested: %s, metadata for file stored in"
                " database: %s",
                ingested_metadata,
                stored_metadata,
            )
            raise RejectRecordError("inconsistent metadata")

    def channel_checks(self):
        """
        Checks if any of the incoming channels exist in the stored record

        if they do they are rejected and a channel response similar to the main channel
        checks is returned
        """
        ingested_channels = self.ingested_record.channels
        stored_channels = self.stored_record.channels

        accepted_channels = []
        rejected_channels = {}

        for channel_name, channel_model in ingested_channels.items():
            if channel_name in stored_channels:
                if isinstance(channel_model, (ImageChannelModel, WaveformChannelModel)):
                    if isinstance(channel_model, ImageChannelModel):
                        path = Image.get_full_path(channel_model.image_path)
                    elif isinstance(channel_model, WaveformChannelModel):
                        path = Waveform.get_full_path(channel_model.waveform_path)

                    object_stored = self._is_image_or_waveform_stored(path)

                if object_stored:
                    rejected_channels[channel_name] = (
                        "Channel is already present in existing record"
                    )
                else:
                    accepted_channels.append(channel_name)
            else:
                accepted_channels.append(channel_name)

        channel_response = {
            "accepted_channels": accepted_channels,
            "rejected_channels": rejected_channels,
        }

        return channel_response

    def _is_image_or_waveform_stored(self, path: str) -> bool:
        """
        Searches for an image or waveform on Echo and returns whether the file is
        present or not
        """

        try:
            self.echo.download_file_object(path)
        except EchoS3Error:
            return False

        return True
