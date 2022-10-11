from collections.abc import MutableMapping
import logging


log = logging.getLogger()


class IngestionValidator:
    def __init__(self, ingested_record, stored_record):
        self.ingested_record = ingested_record
        self.stored_record = stored_record

    # TODO - could be named/placed better?
    @staticmethod
    def search_existing_data(input_data, stored_data):
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
        """
        flat_input_data = IngestionValidator.flatten_data_dict(input_data)
        flat_stored_data = IngestionValidator.flatten_data_dict(stored_data)

        for key in flat_input_data:
            # TODO - this checks if the channels key-value pair is populated, doesn't go
            # any deeper than that. If this is going to be implemented to actually do
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

        return input_data

    # TODO - not used outside of the class, remove static
    # TODO - fix, doesn't work with the record model objects
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
