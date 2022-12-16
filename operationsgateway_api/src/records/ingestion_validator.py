from collections.abc import MutableMapping
import logging

from operationsgateway_api.src.models import RecordModel


log = logging.getLogger()


class IngestionValidator:
    def __init__(self, ingested_record: RecordModel, stored_record: RecordModel):
        self.ingested_record = ingested_record
        self.stored_record = stored_record

    def search_existing_data(self):
        """
        This function searches through the existing shot data stored in MongoDB to see
        if any fields exist in the data extracted from the HDF file

        Flattening the two dictionaries is a good solution if CLF want the API to
        respond with a 4xx error, simply log a warning, or any other action which
        doesn't impact on the input data.

        An alternative implementation should be sought (iterating both dictionaries via
        recursion) if we want to remove the duplicate data. Flattening the dictionaries
        just to iterate through the original data to `del` or `pop()` the pre-existing
        data serves no purpose - we only flatten to make it easier to detect
        pre-existing data.

        This class isn't implemented right now, but will be implemented when use cases
        to reject a file are given. As such, there isn't much purpose in making this
        class work with the refactored code because there are no use cases we can
        implement
        """

        # Check metadata

        # Check channels
        pass

        """
        flat_input_data = IngestionValidator.flatten_data_dict(self.ingested_record)
        flat_stored_data = IngestionValidator.flatten_data_dict(self.stored_record)

        for key in flat_input_data:
            # TODO 2 - this checks if the channels key-value pair is populated, doesn't
            # go any deeper than that. If this is going to be implemented to actually do
            # something, you need to iterate through each channel
            if key in flat_stored_data:
                log.warning(
                    "There's data that already exists in the database, this will be"
                    " overwritten: %s",
                    key,
                )
                # TODO - if we choose to return a 400, implement this
                # Current exception is there as a template only
                # raise Exception("Duplicate data, will not process")

        return self.ingested_record
        """

    # TODO 2 - not used outside of the class, remove static
    # TODO 2 - fix, doesn't work with the record model objects
    @staticmethod
    def flatten_data_dict(data, parent_key=""):
        items = []
        for k, v in data.items():
            new_key = parent_key + "." + k if parent_key else k
            if isinstance(v, MutableMapping):
                items.extend(IngestionValidator.flatten_data_dict(v, new_key).items())
            else:
                items.append((new_key, v))
        return dict(items)
