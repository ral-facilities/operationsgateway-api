from datetime import datetime
import json

from dateutil.parser import parse
from fastapi import Request
import pymongo

from operationsgateway_api.src.exceptions import QueryParameterError


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


class QueryParameterJSONParser:
    def __init__(self, query_param_name: str) -> None:
        self.query_param_name = query_param_name

    def __call__(self, req: Request) -> dict:
        query_param_value = req.query_params.get(self.query_param_name)
        return json.loads(query_param_value) if query_param_value is not None else {}
