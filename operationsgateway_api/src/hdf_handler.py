import collections
import io
import logging

from bson import ObjectId
import h5py

from operationsgateway_api.src.config import Config

log = logging.getLogger()


class HDFDataHandler:
    @staticmethod
    def convert_to_hdf_from_request(request_upload):
        """
        Convert a HDF file that comes attached in a HTTP request (not in HDF format)
        into a HDF file via h5py
        """

        hdf_bytes = io.BytesIO(request_upload)
        return h5py.File(hdf_bytes, "r")

    @staticmethod
    def extract_hdf_data(file_path=None, hdf_file=None):
        """
        Extract data from a HDF file that is formatted in the OperationsGateway data
        structure format. Metadata of the shot, channel data and its metadata is
        extracted. The data is then returned in a dictionary

        For development purposes, a file path can be provided to load a local HDF file
        instead of a file object being passed in
        """

        if file_path:
            hdf_file = h5py.File(file_path, "r")

        record_id = ObjectId()

        record = {"_id": record_id, "metadata": {}, "channels": {}}
        waveforms = []
        images = {}

        for metadata_key, metadata_value in hdf_file.attrs.items():
            log.debug("Metadata Key: %s, Value: %s", metadata_key, metadata_value)

            # Adding metadata of shot
            record["metadata"][metadata_key] = metadata_value

        for column_name, value in hdf_file.items():
            if value.attrs["channel_dtype"] == "image":
                # TODO - should we use a directory per ID? Will need a bit of code added
                # to create directories for each ID to prevent a FileNotFoundError when
                # saving the images
                image_path = (
                    f"{Config.config.mongodb.image_store_directory}/"
                    f"{record['metadata']['shotnum']}_{column_name}.png"
                )
                image_data = value["data"][()]
                images[image_path] = image_data

                record["channels"][column_name] = {
                    "metadata": {},
                    "image_path": image_path,
                }
            elif value.attrs["channel_dtype"] == "rgb-image":
                pass
            elif value.attrs["channel_dtype"] == "scalar":
                record["channels"][column_name] = {"metadata": {}, "data": None}
                record["channels"][column_name]["data"] = value["data"][()]
            elif value.attrs["channel_dtype"] == "waveform":
                # Create a object ID here so it can be assigned to the waveform document
                # and the record before data insertion. This way, we can send the data
                # to the database one after the other. The alternative would be to send
                # the waveform data, fetch the IDs and inject them into the record data
                # which wouldn't be as efficient
                waveform_id = ObjectId()
                log.debug("Waveform ID: %s", waveform_id)
                record["channels"][column_name] = {
                    "metadata": {},
                    "waveform_id": waveform_id,
                }

                waveforms.append(
                    {"_id": waveform_id, "x": value["x"][()], "y": value["y"][()]},
                )

            # Adding channel metadata
            for column_metadata_key, column_metadata_value in value.attrs.items():
                record["channels"][column_name]["metadata"][
                    column_metadata_key
                ] = column_metadata_value

        return record, waveforms, images

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
        flat_input_data = HDFDataHandler.flatten_data_dict(input_data)
        flat_stored_data = HDFDataHandler.flatten_data_dict(stored_data)

        for key in flat_input_data:
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

    @staticmethod
    def flatten_data_dict(data, parent_key=""):
        items = []
        for k, v in data.items():
            new_key = parent_key + "." + k if parent_key else k
            if isinstance(v, collections.MutableMapping):
                items.extend(HDFDataHandler.flatten_data_dict(v, new_key).items())
            else:
                items.append((new_key, v))
        return dict(items)
