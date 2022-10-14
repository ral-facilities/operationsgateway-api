from datetime import datetime
import json
from typing import Optional

from dateutil.parser import parse
import pymongo

from operationsgateway_api.src.exceptions import QueryParameterError


class ParameterHandler:
    @staticmethod
    async def filter_conditions(
        conditions: Optional[str] = None,
    ):
        """
        Converts a JSON string that comes from a query parameter into a Python dict

        FastAPI doesn't directly support dictionary query parameters, so they must be
        converted using `json.loads()` and 'injected' into the endpoint function using
        `Depends()`
        """

        return json.loads(conditions) if conditions is not None else {}

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
                parse(value, fuzzy=False)
            except ValueError:
                # Not a date, nothing to do here
                return

            try:
                new_date = datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
            except ValueError as exc:
                raise QueryParameterError(
                    "Incorrect date format used in query parameter. Use"
                    " %Y-%m-%dT%H:%M:%S to filter by datetimes",
                ) from exc

            return new_date
