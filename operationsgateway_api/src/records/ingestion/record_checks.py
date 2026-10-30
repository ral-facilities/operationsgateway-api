import logging

from operationsgateway_api.src.exceptions import RejectRecordError
from operationsgateway_api.src.models import RecordModel
from operationsgateway_api.src.tags.tag import Tag

log = logging.getLogger()


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
            active_area_type = type(ingested_metadata.active_area)
            if active_area_type != str:
                log.error(
                    "Datatype of active_area is '%s', expected string",
                    active_area_type,
                )
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
            active_experiment_type = type(ingested_metadata.active_experiment)
            if active_experiment_type != str:
                log.error(
                    "Datatype of active_experiment is '%s', expected string",
                    active_experiment_type,
                )
                raise RejectRecordError(
                    "active_experiment has wrong datatype. Expected string",
                )
        if (
            hasattr(ingested_metadata, "shotnum")
            and ingested_metadata.shotnum is not None
        ):
            shotnum_type = type(ingested_metadata.shotnum)
            if shotnum_type not in (int, str):
                log.error(
                    "Datatype of shotnum is '%s', expected integer or string",
                    shotnum_type,
                )
                raise RejectRecordError(
                    "shotnum has wrong datatype. Expected integer or string",
                )

    async def tag_checks(self) -> None:
        """
        Checks that every tag in the record is one of the active tags in the controlled
        vocabulary. The record is rejected if any are not, with the offending tags named
        in the error. Records without tags always pass.
        """
        tags = self.ingested_record.metadata.tags
        if not tags:
            return

        active_tags = {tag.name for tag in await Tag.get_active_tags_from_database()}
        unrecognised_tags = [tag for tag in tags if tag not in active_tags]
        if unrecognised_tags:
            log.error("Tags '%s' are not active tags", unrecognised_tags)
            raise RejectRecordError(
                f"Unrecognised or inactive tags: {', '.join(unrecognised_tags)}",
            )
