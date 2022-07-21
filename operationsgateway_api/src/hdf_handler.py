import collections
import io
import logging

from bson import ObjectId
import h5py
import numpy as np

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

        record = {"_id": record_id, "metadata": {}, "channels": []}
        waveforms = []
        images = {}

        for metadata_key, metadata_value in hdf_file.attrs.items():
            log.debug("Metadata Key: %s, Value: %s", metadata_key, metadata_value)

            # Adding metadata of shot
            record["metadata"][metadata_key] = metadata_value

        for channel_name, value in hdf_file.items():
            channel_data = {"name": channel_name}

            if value.attrs["channel_dtype"] == "image":
                # TODO - should we use a directory per ID? Will need a bit of code added
                # to create directories for each ID to prevent a FileNotFoundError when
                # saving the images
                # TODO - put as a constant/put elsewhere?
                # TODO - separate the code to create an image path into a separate
                # function, this is going to be used in multiple places
                image_path = (
                    f"{Config.config.mongodb.image_store_directory}/"
                    f"{record['metadata']['shotnum']}_{channel_name}.png"
                )
                image_data = value["data"][()]
                images[image_path] = image_data

                channel_data["image_path"] = image_path
            elif value.attrs["channel_dtype"] == "rgb-image":
                # TODO - when we don't want random noise anymore, we could probably
                # combine this code with greyscale images, its the same implementation
                image_path = (
                    f"{Config.config.mongodb.image_store_directory}/"
                    f"{record['metadata']['shotnum']}_{channel_name}.png"
                )

                # Gives random noise, where only example RGB I have sends full black
                # image. Comment out to store true data
                image_data = np.random.randint(
                    0,
                    255,
                    size=(300, 400, 3),
                    dtype=np.uint8,
                )
                images[image_path] = image_data

                channel_data["image_path"] = image_path
            elif value.attrs["channel_dtype"] == "scalar":
                channel_data["data"] = value["data"][()]
            elif value.attrs["channel_dtype"] == "waveform":
                # Create a object ID here so it can be assigned to the waveform document
                # and the record before data insertion. This way, we can send the data
                # to the database one after the other. The alternative would be to send
                # the waveform data, fetch the IDs and inject them into the record data
                # which wouldn't be as efficient
                waveform_id = ObjectId()
                log.debug("Waveform ID: %s", waveform_id)
                channel_data["waveform_id"] = waveform_id

                waveforms.append(
                    {"_id": waveform_id, "x": value["x"][()], "y": value["y"][()]},
                )

            # Adding channel metadata
            channel_data["metadata"] = dict(value.attrs)

            # Adding the processed channel to the record
            record["channels"].append(channel_data)

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

        # Waveform channels are duplicated because the channels are seen as unique to
        # MongoDB due to the differing waveform IDs each time. This loops over waveform
        # channels, ignores the waveform IDs and remove ones that have already been stored
        for stored_channel in stored_data["channels"]:
            if stored_channel["metadata"]["channel_dtype"] == "waveform":
                for input_channel in input_data["channels"].copy():
                    if (
                        input_channel["metadata"]["channel_dtype"] == "waveform"
                        and stored_channel["name"] == input_channel["name"]
                    ):
                        input_waveform = input_channel
                        del input_waveform["waveform_id"]
                        stored_waveform = stored_channel.copy()
                        del stored_waveform["waveform_id"]
                        if input_waveform == stored_waveform:
                            input_data["channels"].remove(input_channel)

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
