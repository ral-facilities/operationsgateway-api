import logging

from operationsgateway_api.src.exceptions import RejectRecordError
from operationsgateway_api.src.models import RecordModel


log = logging.getLogger()


class PartialImportChecks:
    def __init__(self, ingested_record: RecordModel, stored_record: RecordModel):
        """
        This class is instantiated using the record_data form a current stored record
        and from an incoming record using hdf_handler
        """
        self.ingested_record = ingested_record
        self.stored_record = stored_record

    def metadata_checks(self):
        """
        Compares the metadata of both files and decides what to do from there

        it can:
            accept as a new record
            merge the record
            reject the record
        """
        ingested_metadata = (self.ingested_record).metadata
        stored_metadata = (self.stored_record).metadata

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
            raise RejectRecordError("inconsistent metadata")

    def channel_checks(self):
        """
        Checks if any of the incoming channels exist in the stored record

        if they do they are rejected and a channel response similar to the main channel
        checks is returned
        """
        ingested_channels = (self.ingested_record).channels
        stored_channels = (self.stored_record).channels

        accepted_channels = []
        rejected_channels = {}

        for key in list(ingested_channels.keys()):
            if key in stored_channels:
                rejected_channels[key] = "Channel is already present in existing record"
            else:
                accepted_channels.append(key)

        channel_response = {
            "accepted_channels": accepted_channels,
            "rejected_channels": rejected_channels,
        }

        return channel_response
