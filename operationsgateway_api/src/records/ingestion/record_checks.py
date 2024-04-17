import logging

from operationsgateway_api.src.exceptions import RejectRecordError
from operationsgateway_api.src.models import RecordModel


class RecordChecks:
    def __init__(self, ingested_record: RecordModel):
        """
        This class is instantiated using the RecordModel from running hdf_handler
        """
        self.ingested_record = ingested_record

    def active_area_checks(self):
        """
        Checks if active area is missing or if its not a string
        it will reject the record if so
        """
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
        """
        Checks if active_experiment and shotnum have incorrect datatypes
        if they do the record is rejected (no need to reject if they don't exist
        because they are optional)
        """
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
