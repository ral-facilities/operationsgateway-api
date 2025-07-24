import logging

from operationsgateway_api.src.exceptions import RejectRecordError
from operationsgateway_api.src.models import (
    FloatImageChannelModel,
    ImageChannelModel,
    RecordModel,
    VectorChannelModel,
    WaveformChannelModel,
)
from operationsgateway_api.src.records.echo_interface import get_echo_interface
from operationsgateway_api.src.records.float_image import FloatImage
from operationsgateway_api.src.records.image import Image
from operationsgateway_api.src.records.vector import Vector
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
        self.echo_interface = get_echo_interface()

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

        # Match timestamp with or without timezone info
        try:
            time_match = ingested_metadata.timestamp.replace(
                tzinfo=None,
            ) == stored_metadata.timestamp.replace(tzinfo=None)
        except Exception:
            time_match = ingested_metadata.timestamp == stored_metadata.timestamp

        area_match = ingested_metadata.active_area == stored_metadata.active_area
        experiment_match = (
            ingested_metadata.active_experiment == stored_metadata.active_experiment
        )

        shot_match = ingested_metadata.shotnum == stored_metadata.shotnum

        # Reject if shotnum matches but timestamp doesn't
        if shot_match and not time_match:
            raise RejectRecordError("a record with this shotnum already exists")

        # Accept merge if everything matches
        if shot_match and time_match and area_match and experiment_match:
            log.info("record metadata matches existing record perfectly")
            return "accept_merge"

        # Accept as new record if both timestamp and shotnum are unique
        if not time_match and not shot_match:
            return "accept_new"

        # All other cases are inconsistent
        log.error(
            "Metadata for file being ingested: %s, metadata for file "
            "stored in database: %s",
            ingested_metadata,
            stored_metadata,
        )
        raise RejectRecordError("inconsistent metadata")

    def channel_checks(
        self,
        channel_dict: dict[str, list[str] | dict[str, str]],
    ) -> dict[str, list[str] | dict[str, str]]:
        """
        Checks if any of the incoming channels exist in the stored record. If the
        channels exist, they're rejected, otherwise they become an accepted channel.

        For image and waveform channels, a check is conducted to determine whether the
        associated image/waveform is stored in Echo; there could be a situation where
        there's an image channel in the record, but the image isn't stored in Echo
        (perhaps due to a failure in ingestion or someone's manually deleted it)
        """
        accepted_channels = []
        rejected_channels = {}

        for channel_name, channel_model in self.ingested_record.channels.items():
            if channel_name in self.stored_record.channels:
                if isinstance(channel_model, ImageChannelModel):
                    path = Image.get_full_path(channel_model.image_path)
                    object_stored = self.echo_interface.head_object(path)
                elif isinstance(channel_model, FloatImageChannelModel):
                    path = FloatImage.get_full_path(channel_model.image_path)
                    object_stored = self.echo_interface.head_object(path)
                elif isinstance(channel_model, WaveformChannelModel):
                    path = Waveform.get_full_path(channel_model.waveform_path)
                    object_stored = self.echo_interface.head_object(path)
                elif isinstance(channel_model, VectorChannelModel):
                    path = Vector.get_full_path(channel_model.vector_path)
                    object_stored = self.echo_interface.head_object(path)
                else:
                    object_stored = True
                if object_stored:
                    rejected_channels[channel_name] = (
                        "Channel is already present in existing record"
                    )
                else:
                    accepted_channels.append(channel_name)
            else:
                accepted_channels.append(channel_name)

        log.info("existent record found")
        for key, value in channel_dict["rejected_channels"].items():
            rejected_channels[key] = value
            if key in accepted_channels:
                accepted_channels.remove(key)

        return {
            "accepted_channels": accepted_channels,
            "rejected_channels": rejected_channels,
        }
