import base64
import logging

from bson import ObjectId
import numpy

log = logging.getLogger()


class DataEncoding:
    @staticmethod
    def encode_object_id(id_):
        """
        Encode the provided ID to an object ID ready to be inserted into MongoDB
        """

        return ObjectId(id_)

    @staticmethod
    # TODO - allow input to be multiple things which can be unpacked. List/kwargs??
    def encode_numpy_for_mongo(data):
        """
        Encode the provided data to be stored in the appropriate formats for MongoDB
        """

        for key, value in data.items():
            data[key] = DataEncoding.data_conversion(value)

    @staticmethod
    def data_conversion(value):
        """
        Convert data values into more appropriate formats ready to be stored in MongoDB

        This is a recursive function so is suitable for use with nested documents. If a
        value type isn't by the function, a warning will be logged, but no error will be
        thrown
        """

        new_value = None

        if isinstance(value, dict):
            for inner_key, inner_value in value.items():
                new_new_value = DataEncoding.data_conversion(inner_value)
                value[inner_key] = new_new_value
            new_value = value
        elif isinstance(value, numpy.int64) or isinstance(value, numpy.uint64):
            new_value = int(value)
        elif isinstance(value, numpy.float64):
            new_value = float(value)
        elif isinstance(value, numpy.ndarray) and len(value.shape) == 1:
            # For 1D arrays in traces
            new_value = str(list(value))
        elif isinstance(value, numpy.ndarray) and len(value.shape) == 2:
            # TODO - might not be needed as we'll be storing images on disk
            # For images
            new_value = base64.b64encode(value)
        elif (
            isinstance(value, str)
            or isinstance(value, bytes)
            or isinstance(value, ObjectId)
        ):
            new_value = value
        else:
            log.warning("Type not caught: %s, Value: %s", type(value), value)

        return new_value
