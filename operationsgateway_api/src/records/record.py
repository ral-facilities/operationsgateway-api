import base64
from datetime import datetime
import logging
from typing import Any, Dict, List, Tuple, Union

import numpy as np
from PIL import Image as PILImage
from pydantic import ValidationError
import pymongo
from pymongo.results import DeleteResult

from operationsgateway_api.src.exceptions import (
    ChannelSummaryError,
    DatabaseError,
    FunctionParseError,
    MissingDocumentError,
    ModelError,
    RecordError,
)
from operationsgateway_api.src.functions import (
    ExpressionTransformer,
    VariableTransformer,
    WaveformVariable,
)
from operationsgateway_api.src.models import (
    DateConverterRange,
    RecordModel,
    ShotnumConverterRange,
)
from operationsgateway_api.src.mongo.interface import MongoDBInterface
from operationsgateway_api.src.records.false_colour_handler import FalseColourHandler
from operationsgateway_api.src.records.image import Image
from operationsgateway_api.src.records.waveform import Waveform


log = logging.getLogger()


class Record:
    def __init__(self, record: RecordModel) -> None:
        """
        Store a record within the object. If the input is a dictionary, it will be
        converted into a `RecordModel` object
        """
        if isinstance(record, RecordModel):
            self.record = record
        elif isinstance(record, dict):
            try:
                self.record = RecordModel(**record)
            except ValidationError as exc:
                raise ModelError(str(exc)) from exc
        else:
            raise RecordError("RecordModel or dictionary not passed to Record init")

    def store_thumbnail(self, data: Union[Image, Waveform]) -> None:
        """
        Extract a thumbnail from a given image or waveform and store it in the record
        object so it can be inserted in the database as part of the record
        """
        if isinstance(data, Image):
            _, channel_name = data.extract_metadata_from_path()
        elif isinstance(data, Waveform):
            channel_name = data.get_channel_name_from_id()

        self.record.channels[channel_name].thumbnail = data.thumbnail

    async def insert(self) -> None:
        """
        Use the `MongoDBInterface` to insert the object's record into the `records`
        collection in the database
        """
        await MongoDBInterface.insert_one(
            "records",
            self.record.model_dump(by_alias=True, exclude_unset=True),
        )

    async def update(self) -> None:
        """
        Update a record which already exists in the database

        This update query has been split into two one (which is iterated in a loop) to
        add record metadata, and another to add each of the channels. Based on some
        quick dev testing while making sure it worked, this doesn't slow down ingestion
        times
        """

        for metadata_key, value in self.record.metadata.model_dump(
            exclude_unset=True,
        ).items():
            await MongoDBInterface.update_one(
                "records",
                {"_id": self.record.id_},
                {"$set": {f"metadata.{metadata_key}": value}},
            )

        for channel_name, channel_value in self.record.channels.items():
            await MongoDBInterface.update_one(
                "records",
                {"_id": self.record.id_},
                {
                    "$set": {
                        f"channels.{channel_name}": channel_value.model_dump(
                            exclude_unset=True,
                        ),
                    },
                },
            )

    async def find_existing_record(self) -> Union[RecordModel, None]:
        """
        Using the ID, check if the object's record is currently stored in the database
        or not. Return the data in a `RecordModel` if so, otherwise `None` will be
        returned
        """

        log.debug(
            "Querying MongoDB to see if a record is already stored in the database",
        )
        record_dict = await MongoDBInterface.find_one(
            "records",
            filter_={"_id": self.record.id_},
        )

        if record_dict:
            existing_record = RecordModel(
                _id=record_dict["_id"],
                metadata=record_dict["metadata"],
                channels=record_dict["channels"],
            )
            return existing_record
        else:
            return None

    @staticmethod
    async def find_record(
        conditions: Dict[str, Any],
        skip: int,
        limit: int,
        sort: List[Tuple[str, int]],
        projection: List[str],
    ) -> List[dict]:
        """
        Using the database query parameters, find record(s) that match the query and
        return them
        """
        records_query = MongoDBInterface.find(
            collection_name="records",
            filter_=conditions,
            skip=skip,
            limit=limit,
            sort=sort,
            projection=projection,
        )
        records_data = await MongoDBInterface.query_to_list(records_query)
        return records_data

    @staticmethod
    async def find_record_by_id(
        id_: str,
        conditions: Dict[str, Any],
        projection: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Given an ID and any number of conditions, find a single record and return it. If
        the record cannot be found, a `MissingDocumentError` will be raised instead
        """
        record_data = await MongoDBInterface.find_one(
            "records",
            {"_id": id_, **conditions},
            projection=projection,
        )

        if record_data:
            return record_data
        else:
            log.error("Record cannot be found. ID: %s, Conditions: %s", id_, conditions)
            raise MissingDocumentError("Record cannot be found")

    @staticmethod
    async def get_date_of_channel_data(
        channel_name: str,
        direction: List[tuple],
    ) -> datetime:
        """
        Depending on the direction given, either get the date of the newest or oldest
        piece of data that exists for a particular channel. If no data can be found, a
        `ChannelSummaryError` will be raised
        """
        channel_exist_condiion = {f"channels.{channel_name}": {"$exists": True}}
        data = await MongoDBInterface.find_one(
            "records",
            filter_=channel_exist_condiion,
            sort=direction,
            projection=["metadata.timestamp"],
        )

        if data:
            return data["metadata"]["timestamp"]
        else:
            raise ChannelSummaryError(
                f"There is no timestamp data for {channel_name}",
            )

    @staticmethod
    async def get_recent_channel_values(
        channel_name: str,
        colourmap_name: str,
    ) -> List[Union[str, int, float]]:
        """
        Return the most recent three values for a particular channel

        Depending on the channel type, different samples will be collected:
        - Scalar: return the values themselves
        - Image or waveform: return the thumbnails of the data they represent
        """

        channel_path = f"channels.{channel_name}"
        channel_exist_condiion = {channel_path: {"$exists": True}}

        recent_channel_query = MongoDBInterface.find(
            "records",
            filter_=channel_exist_condiion,
            limit=3,
            sort=[("_id", pymongo.DESCENDING)],
            projection=[f"channels.{channel_name}", "metadata"],
        )
        recent_channel_data = await MongoDBInterface.query_to_list(recent_channel_query)
        records = [RecordModel(**record) for record in recent_channel_data]

        recent_values = []
        for record in records:
            channel = record.channels[channel_name]

            if channel.metadata.channel_dtype == "scalar":
                recent_values.append({record.metadata.timestamp: channel.data})
            elif channel.metadata.channel_dtype == "image":
                thumbnail_bytes = FalseColourHandler.apply_false_colour_to_b64_img(
                    channel.thumbnail,
                    None,
                    None,
                    colourmap_name,
                )
                thumbnail_bytes.seek(0)
                recent_values.append(
                    {
                        record.metadata.timestamp: base64.b64encode(
                            thumbnail_bytes.getvalue(),
                        ),
                    },
                )
            elif channel.metadata.channel_dtype == "waveform":
                recent_values.append({record.metadata.timestamp: channel.thumbnail})

        return recent_values

    @staticmethod
    async def count_records(conditions: Dict[str, Any]) -> int:
        return await MongoDBInterface.count_documents("records", conditions)

    @staticmethod
    async def delete_record(id_: str) -> DeleteResult:
        return await MongoDBInterface.delete_one("records", {"_id": id_})

    @staticmethod
    def truncate_thumbnails(record: Dict[str, Any]) -> None:
        """
        Quality of life functionality for developers that chops the thumbnail strings so
        they don't bloat the API clients being used to test
        """
        for value in record["channels"].values():
            try:
                value["thumbnail"] = value["thumbnail"][:50]
            except KeyError:
                # If there's no thumbnails (e.g. if channel isn't an image or waveform)
                # then a KeyError will be raised. This is normal behaviour, so
                # acceptable to pass
                pass

    @staticmethod
    async def apply_false_colour_to_thumbnails(
        record: dict,
        lower_level: int,
        upper_level: int,
        colourmap_name: str,
    ) -> None:
        """
        Apply false colour to any greyscale image thumbnails in the record.

        Iterate through the channels in the record looking for ones that have the type
        'image'.
        These will be the greyscale images which need to have false colour applied.
        Note: there will also be "thumbnail" entries in 'rgb-image' and 'waveform'
        channels but they should not have false colour applied to them.
        """
        record_id = record["_id"]
        for channel_name, value in record["channels"].items():
            channel_dtype = await Record.get_channel_dtype(
                record_id,
                channel_name,
                value,
            )
            try:
                if channel_dtype == "image":
                    b64_thumbnail_str = value["thumbnail"]
                    thumbnail_bytes = FalseColourHandler.apply_false_colour_to_b64_img(
                        b64_thumbnail_str,
                        lower_level,
                        upper_level,
                        colourmap_name,
                    )
                    thumbnail_bytes.seek(0)
                    value["thumbnail"] = base64.b64encode(thumbnail_bytes.getvalue())
            except KeyError:
                # If there's no thumbnail (e.g. if channel isn't an image or waveform)
                # then a KeyError will be raised. This is normal behaviour, so
                # acceptable to pass
                pass

    @staticmethod
    async def get_channel_dtype(
        record_id: str,
        channel_name: str,
        channel_value: dict,
    ) -> str:
        """
        Extract "channel_dtype" from `channel_value`, or if not present, retrieve with a
        separate lookup.
        """
        try:
            channel_dtype = channel_value["metadata"]["channel_dtype"]
        except KeyError:
            # if a projection has been applied then the record will only contain
            # the requested fields and probably not the channel_dtype
            # so it needs to be looked up separately
            record_dict = await Record.find_record_by_id(
                record_id,
                {},
                [f"channels.{channel_name}.metadata.channel_dtype"],
            )
            new_channel_value = record_dict["channels"][channel_name]
            channel_dtype = new_channel_value["metadata"]["channel_dtype"]

        return channel_dtype

    @staticmethod
    async def convert_search_ranges(date_range, shotnum_range):
        if date_range:
            # Convert date range to shot number range
            comparison_field_name = "metadata.timestamp"
            output_field_name = "$metadata.shotnum"
            min_field_name = "min"
            max_field_name = "max"

            try:
                range_input = DateConverterRange(**date_range)
            except ValidationError as exc:
                raise ModelError(str(exc)) from exc
        elif shotnum_range:
            # Convert shot number range to date range
            comparison_field_name = "metadata.shotnum"
            output_field_name = "$metadata.timestamp"
            min_field_name = "from"
            max_field_name = "to"

            try:
                range_input = ShotnumConverterRange(**shotnum_range)
            except ValidationError as exc:
                raise ModelError(str(exc)) from exc
        else:
            raise RecordError("Both date range and shot number range are None")

        pipeline = [
            {
                "$match": {
                    "$and": [
                        {
                            comparison_field_name: {
                                "$gte": getattr(
                                    range_input,
                                    range_input.opposite_range_fields[min_field_name],
                                ),
                                "$lte": getattr(
                                    range_input,
                                    range_input.opposite_range_fields[max_field_name],
                                ),
                            },
                        },
                    ],
                },
            },
            {
                "$group": {
                    "_id": None,
                    min_field_name: {"$min": output_field_name},
                    max_field_name: {"$max": output_field_name},
                },
            },
        ]

        converted_range = await MongoDBInterface.aggregate("records", pipeline)
        if len(converted_range) == 0:
            # This could be because dates/shot numbers provided are out of range, i.e.
            # there's no records stored in the ranges provided by the request, hence
            # the database is unable to find anything from the query
            raise DatabaseError("No results have been found from database query")

        try:
            if shotnum_range:
                return DateConverterRange(**converted_range[0])
            else:
                return ShotnumConverterRange(**converted_range[0])
        except ValidationError as exc:
            raise ModelError(str(exc)) from exc

    @staticmethod
    async def apply_functions(
        record: dict[str, dict],
        functions: list,
        lower_level: int,
        upper_level: int,
        colourmap_name: str,
        truncate_response: bool = True,
    ) -> None:
        """
        Evaluates all functions and stores the results on `record` as though
        they were normal channels.
        """
        variable_data = {}
        Record._ensure_channels(record)

        variable_transformer = VariableTransformer()
        expression_transformer = ExpressionTransformer(variable_data)
        for function in functions:
            await Record._apply_function(
                record,
                lower_level,
                upper_level,
                colourmap_name,
                variable_data,
                variable_transformer,
                expression_transformer,
                function,
                truncate_response,
            )

    @staticmethod
    def _ensure_channels(record):
        if "channels" not in record:
            record["channels"] = {}

    @staticmethod
    async def _apply_function(
        record: dict[str, dict],
        lower_level: int,
        upper_level: int,
        colourmap_name: str,
        variable_data: dict,
        variable_transformer: VariableTransformer,
        expression_transformer: ExpressionTransformer,
        function: dict,
        truncate_response: bool = True,
    ) -> None:
        """
        Evaluates a single function and stores the result on `record` as though
        it were a normal channel.
        """
        variable_transformer.evaluate(function["expression"])
        variables = variable_transformer.variables
        channels_to_fetch = set()

        for variable in variables:
            if variable in record["channels"]:
                variable_data[variable] = await Record._extract_variable(
                    record["_id"],
                    variable,
                    record["channels"][variable],
                )
            else:
                channels_to_fetch.add(variable)

        if channels_to_fetch:
            log.debug("Fetching channels: %s", channels_to_fetch)
            record_extra = await Record.find_record_by_id(
                record["_id"],
                {},
                [f"channels.{v}" for v in channels_to_fetch],
            )

            fetched_channels: dict = record_extra["channels"]
            missing_channels = channels_to_fetch.difference(fetched_channels)
            if missing_channels:
                message = f"Unable to parse variables: {missing_channels}"
                raise FunctionParseError(message)

            for name, channel_value in fetched_channels.items():
                variable_data[name] = await Record._extract_variable(
                    record["_id"],
                    name,
                    channel_value,
                )

        result = expression_transformer.evaluate(function["expression"])
        Record._parse_function_results(
            record,
            lower_level,
            upper_level,
            colourmap_name,
            function["name"],
            result,
            truncate_response,
        )
        variable_data[function["name"]] = result

    @staticmethod
    async def _extract_variable(
        record_id: str,
        name: str,
        channel_value: dict,
    ) -> np.ndarray | WaveformVariable | float:
        """
        Extracts and returns the relevant data from `channel_value`, handling
        extra calls needed for "image" and "waveform" types.
        """
        channel_dtype = await Record.get_channel_dtype(
            record_id=record_id,
            channel_name=name,
            channel_value=channel_value,
        )
        if channel_dtype == "image":
            # Loading from echo takes ~ 0.2 s per image
            image_bytes = await Image.get_image(
                record_id,
                name,
                True,
                0,
                255,
                None,
            )
            img_src = PILImage.open(image_bytes)
            img_array = np.array(img_src)
            # TODO data quality lacking, unclear if this is true 32 bit, 16
            # bit shifted etc. Needs to be resolved for generated data
            img_array //= 256
            return img_array
        elif channel_dtype == "waveform":
            waveform_id = channel_value["waveform_id"]
            waveform = await Waveform.get_waveform(waveform_id)
            return WaveformVariable(waveform)
        else:
            return channel_value["data"]

    @staticmethod
    def _parse_function_results(
        record: dict,
        lower_level: int,
        upper_level: int,
        colourmap_name: str,
        function_name: str,
        result: np.ndarray | WaveformVariable | np.float64,
        truncate_response: bool = True,
    ) -> None:
        """
        Parses the numerical `result` and modifies `record` in place to contain
        the data in the expected format for the type of the `result`.
        """
        Record._ensure_channels(record)

        if isinstance(result, np.ndarray):
            if truncate_response:
                metadata = {
                    "channel_dtype": "image",
                    "x_pixel_size": result.shape[1],
                    "y_pixel_size": result.shape[0],
                }
                step_size = max(*result.shape) // 50
                image_array = result[::step_size, ::step_size]
                image_bytes = FalseColourHandler.apply_false_colour(
                    image_array,
                    8,  # TODO handle depth dynamically, based on the array?
                    lower_level,
                    upper_level,
                    colourmap_name,
                )
                image_bytes.seek(0)
                image_b64 = base64.b64encode(image_bytes.getvalue())
                channel = {
                    "thumbnail": image_b64,
                    "metadata": metadata,
                }
            else:
                image_bytes = FalseColourHandler.apply_false_colour(
                    result,
                    8,  # TODO handle depth dynamically, based on the array?
                    lower_level,
                    upper_level,
                    colourmap_name,
                )
                image_bytes.seek(0)
                channel = {"data": image_bytes}

        elif isinstance(result, WaveformVariable):
            if truncate_response:
                waveform = result.to_waveform()
                # Creating thumbnail takes ~ 0.05 s per waveform
                waveform.create_thumbnail()
                metadata = {"channel_dtype": "waveform"}
                channel = {
                    "thumbnail": waveform.thumbnail,
                    "metadata": metadata,
                }
            else:
                waveform_model = result.to_waveform_model()
                channel = {"data": waveform_model}

        else:
            metadata = {"channel_dtype": "scalar"}
            # Cannot return np.float64 as it can't be cast to JSON
            channel = {"data": float(result), "metadata": metadata}

        record["channels"][function_name] = channel
