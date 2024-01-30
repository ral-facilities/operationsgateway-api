from datetime import datetime

import pymongo


class ParameterHandler:
    @staticmethod
    def extract_order_data(orders):
        """
        Given a string of the order portion of a MongoDB query, put it into a format
        that PyMongo can understand

        An example input string: `[channel_name.title asc, shotnum desc]`
        """

        sort_data = []

        for order in orders:
            field = order.split(" ")[0]
            direction = order.split(" ")[1]

            if direction.lower() == "asc":
                direction = pymongo.ASCENDING
            elif direction.lower() == "desc":
                direction = pymongo.DESCENDING
            else:
                raise ValueError(
                    "Invalid direction given in order parameter, please try again",
                )

            sort_data.append((field, direction))

        return sort_data

    @staticmethod
    def encode_date_for_conditions(value):
        new_date = None

        if isinstance(value, dict):
            for inner_key, inner_value in value.items():
                new_new_date = ParameterHandler.encode_date_for_conditions(inner_value)
                if new_new_date is not None:
                    value[inner_key] = new_new_date
        elif isinstance(value, list):
            for element in value:
                ParameterHandler.encode_date_for_conditions(element)
        elif isinstance(value, str):
            try:
                new_date = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
            except ValueError:
                # Not a date in the correct format, nothing to do here
                return
            return new_date
