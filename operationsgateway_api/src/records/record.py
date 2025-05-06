import base64
from datetime import datetime
from io import BytesIO
import logging
from typing import Any, Dict, List, Tuple, Union

import numpy as np
from PIL import Image as PILImage
from pydantic import ValidationError
import pymongo
from pymongo.results import DeleteResult

from operationsgateway_api.src.channels.channel_manifest import ChannelManifest
from operationsgateway_api.src.config import Config
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
from operationsgateway_api.src.functions.variable_models import (
    PartialImageVariableChannelModel,
    PartialVariableChannelModel,
    PartialVariableChannels,
    PartialWaveformVariableChannelModel,
)
from operationsgateway_api.src.models import (
    ChannelDtype,
    DateConverterRange,
    PartialChannelModel,
    PartialRecordModel,
    PartialScalarChannelModel,
    RecordModel,
    ShotnumConverterRange,
)
from operationsgateway_api.src.mongo.interface import MongoDBInterface
from operationsgateway_api.src.records.false_colour_handler import FalseColourHandler
from operationsgateway_api.src.records.float_image import FloatImage
from operationsgateway_api.src.records.image import Image
from operationsgateway_api.src.records.vector import Vector
from operationsgateway_api.src.records.waveform import Waveform


log = logging.getLogger()


class Record:
    def __init__(self, record: Union[RecordModel, dict]) -> None:
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

    def store_thumbnail(self, data: Image | FloatImage | Waveform | Vector) -> None:
        """
        Extract a thumbnail from a given image, vector or waveform and store it in the
        record object so it can be inserted in the database as part of the record
        """
        channel_name = data.get_channel_name_from_path()
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

    def remove_channel(self, channel_name: str) -> None:
        if channel_name in self.record.channels:
            log.info("Removing channel '%s' from record.", channel_name)
            del self.record.channels[channel_name]
        else:
            log.error("Channel '%s' not found in record.", channel_name)

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
    ) -> list[PartialRecordModel]:
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
        return [PartialRecordModel(**record) for record in records_data]

    @staticmethod
    async def find_record_by_id(
        id_: str,
        conditions: Dict[str, Any],
        projection: List[str] = None,
    ) -> PartialRecordModel:
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
            return PartialRecordModel(**record_data)
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
        channel_exist_condition = {f"channels.{channel_name}": {"$exists": True}}
        data = await MongoDBInterface.find_one(
            "records",
            filter_=channel_exist_condition,
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
        float_colourmap: str,
    ) -> List[Union[str, int, float]]:
        """
        Return the most recent three values for a particular channel

        Depending on the channel type, different samples will be collected:
        - Scalar: return the values themselves
        - Image, float image, waveform or vector: return the thumbnails of the data they
          represent
        """

        channel_path = f"channels.{channel_name}"
        channel_exist_condition = {channel_path: {"$exists": True}}

        recent_channel_query = MongoDBInterface.find(
            "records",
            filter_=channel_exist_condition,
            limit=3,
            sort=[("_id", pymongo.DESCENDING)],
            projection=[f"channels.{channel_name}", "metadata"],
        )
        recent_channel_data = await MongoDBInterface.query_to_list(recent_channel_query)
        records = [RecordModel(**record) for record in recent_channel_data]

        recent_values = []
        for record in records:
            channel = record.channels[channel_name]
            data = None

            if channel.metadata.channel_dtype == "scalar":
                data = channel.data
            elif channel.metadata.channel_dtype == "image":
                thumbnail_bytes = FalseColourHandler.apply_false_colour_to_b64_img(
                    channel.thumbnail,
                    None,
                    None,
                    colourmap_name,
                )
                data = base64.b64encode(thumbnail_bytes.getvalue())
            elif channel.metadata.channel_dtype == "waveform":
                data = channel.thumbnail
            elif channel.metadata.channel_dtype == ChannelDtype.VECTOR:
                data = channel.thumbnail
            elif channel.metadata.channel_dtype == ChannelDtype.FLOAT_IMAGE:
                bytes_io = FalseColourHandler.apply_false_colour_to_b64_float_img(
                    channel.thumbnail,
                    float_colourmap,
                )
                data = base64.b64encode(bytes_io.getvalue())
            else:
                msg = "Unrecognised channel_dtype of %s"
                log.warning(msg, channel.metadata.channel_dtype)
                continue

            recent_values.append({record.metadata.timestamp: data})

        return recent_values

    @staticmethod
    async def count_records(conditions: Dict[str, Any]) -> int:
        return await MongoDBInterface.count_documents("records", conditions)

    @staticmethod
    async def delete_record(id_: str) -> DeleteResult:
        return await MongoDBInterface.delete_one("records", {"_id": id_})

    @staticmethod
    def truncate_thumbnails(record: PartialRecordModel) -> None:
        """
        Quality of life functionality for developers that chops the thumbnail strings so
        they don't bloat the API clients being used to test
        """
        for value in record.channels.values():
            try:
                value.thumbnail = value.thumbnail[:50]
            except (AttributeError, TypeError):
                # If there's no thumbnails (e.g. if channel isn't an image or waveform)
                # then an AttributeError will be raised. If the thumbnail is None, a
                # TypeError will be raised. This is normal behaviour, so acceptable to
                # pass
                pass

    @staticmethod
    async def apply_false_colour_to_thumbnails(
        record: PartialRecordModel,
        lower_level: int,
        upper_level: int,
        colourmap_name: str,
        float_colourmap_name: str,
    ) -> None:
        """
        Apply false colour to any greyscale image thumbnails in the record.

        Iterate through the channels in the record looking for ones that have the type
        'image'.
        These will be the greyscale images which need to have false colour applied.
        Note: there will also be "thumbnail" entries in 'rgb-image' and 'waveform'
        channels but they should not have false colour applied to them.
        """
        record_id = record.id_
        for channel_name, value in record.channels.items():
            channel_dtype = await Record.get_channel_dtype(
                record_id,
                channel_name,
                value,
            )
            b64_thumbnail_str = getattr(value, "thumbnail", None)
            if b64_thumbnail_str is not None:
                if channel_dtype == "image":
                    thumbnail_bytes = FalseColourHandler.apply_false_colour_to_b64_img(
                        b64_thumbnail_str,
                        lower_level,
                        upper_level,
                        colourmap_name,
                    )
                    value.thumbnail = base64.b64encode(thumbnail_bytes.getvalue())
                elif channel_dtype == "float_image":
                    thumbnail_bytes = (
                        FalseColourHandler.apply_false_colour_to_b64_float_img(
                            b64_thumbnail_str,
                            float_colourmap_name,
                        )
                    )
                    value.thumbnail = base64.b64encode(thumbnail_bytes.getvalue())

    @staticmethod
    async def get_channel_dtype(
        record_id: str,
        channel_name: str,
        channel_value: PartialChannelModel,
    ) -> ChannelDtype:
        """
        Extract "channel_dtype" from `channel_value`, or if not present, retrieve with a
        separate lookup.
        """
        try:
            channel_dtype = channel_value.metadata.channel_dtype
        except AttributeError:
            # if a projection has been applied then the record will only contain
            # the requested fields and probably not the channel_dtype
            # so it needs to be looked up separately
            record = await Record.find_record_by_id(
                record_id,
                {},
                [f"channels.{channel_name}.metadata.channel_dtype"],
            )
            channel_dtype = record.channels[channel_name].metadata.channel_dtype

        return channel_dtype

    @staticmethod
    async def get_raw_bit_depth(
        record_id: str,
        channel_name: str,
        channel_value: PartialChannelModel,
    ) -> "int | None":
        """
        Extract "bit_depth" from `channel_value`, or if not present, retrieve with a
        separate lookup.

        Args:
            record_id (str): Record identifier
            channel_name (str): Channel name to get the bit depth for
            channel_value (dict):
                Previously fetched channel (may not include all the metadata).

        Returns:
            int | None: The bit_depth if found, `None` otherwise.
        """
        try:
            raw_bit_depth = channel_value.metadata.bit_depth
        except AttributeError:
            # if a projection has been applied then the record will only contain
            # the requested fields and probably not the channel_dtype
            # so it needs to be looked up separately
            record_dict = await Record.find_record_by_id(
                record_id,
                {},
                [f"channels.{channel_name}.metadata.bit_depth"],
            )
            raw_bit_depth = record_dict.channels[channel_name].metadata.bit_depth

        return raw_bit_depth

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
        record: PartialRecordModel,
        functions: "list[dict[str, str]]",
        original_image: bool,
        lower_level: int,
        upper_level: int,
        limit_bit_depth: int,
        colourmap_name: str,
        return_thumbnails: bool = True,
        truncate: bool = False,
    ) -> PartialVariableChannels:
        """
        Evaluates all functions and stores the results on `record` as though
        they were normal channels.
        """
        variable_data = {}
        channels = {}
        if record.channels is not None:
            channels.update(record.channels)

        variable_transformer = VariableTransformer()
        expression_transformer = ExpressionTransformer(variable_data)
        for function in functions:
            await Record._apply_function(
                record_id=record.id_,
                channels=channels,
                original_image=original_image,
                lower_level=lower_level,
                upper_level=upper_level,
                limit_bit_depth=limit_bit_depth,
                colourmap_name=colourmap_name,
                variable_data=variable_data,
                variable_transformer=variable_transformer,
                expression_transformer=expression_transformer,
                function=function,
                return_thumbnails=return_thumbnails,
                truncate=truncate,
            )

        record.channels = channels
        return channels

    @staticmethod
    async def _apply_function(
        record_id: str,
        channels: PartialVariableChannels,
        original_image: bool,
        lower_level: int,
        upper_level: int,
        limit_bit_depth: int,
        colourmap_name: str,
        variable_data: dict,
        variable_transformer: VariableTransformer,
        expression_transformer: ExpressionTransformer,
        function: "dict[str, str]",
        return_thumbnails: bool = True,
        truncate: bool = False,
    ) -> None:
        """
        Evaluates a single function and stores the result on `record` as though
        it were a normal channel.
        """
        variable_transformer.evaluate(function["expression"])
        variables = variable_transformer.variables
        channels_to_fetch = set()
        bit_depths = []

        log.debug("Attempting to extract %s from %s", variables, channels)
        for variable in variables:
            if variable in channels:
                variable_data[variable] = await Record._extract_variable(
                    record_id=record_id,
                    name=variable,
                    channel_value=channels[variable],
                    bit_depths=bit_depths,
                )
            else:
                channels_to_fetch.add(variable)

        if channels_to_fetch:
            missing_channels = await Record._fetch_channels(
                record_id=record_id,
                variable_data=variable_data,
                channels_to_fetch=channels_to_fetch,
                skip_functions=variable_transformer.skip_functions,
                bit_depths=bit_depths,
            )
            if missing_channels:
                # Remove any missing channels so we don't skip future functions which
                # may not depend on them
                variable_transformer.variables -= missing_channels
                variable_transformer.skip_functions.add(function["name"])
                return

        result = expression_transformer.evaluate(function["expression"])
        channel = Record._parse_function_results(
            original_image=original_image,
            lower_level=lower_level,
            upper_level=upper_level,
            limit_bit_depth=limit_bit_depth,
            colourmap_name=colourmap_name,
            result=result,
            return_thumbnails=return_thumbnails,
            truncate=truncate,
            bit_depths=bit_depths,
        )
        channels[function["name"]] = channel
        variable_data[function["name"]] = result

    @staticmethod
    async def _fetch_channels(
        record_id: str,
        variable_data: dict,
        channels_to_fetch: "set[str]",
        skip_functions: "set[str]",
        bit_depths: "list[int]",
    ) -> "set[str]":
        """Fetches `channels_to_fetch`, returning known channels missing for this
        record and raising an exception if the channel is not known at all."""
        log.debug("Fetching channels: %s", channels_to_fetch)
        projection = [f"channels.{v}" for v in channels_to_fetch]
        record_extra = await Record.find_record_by_id(record_id, {}, projection)
        fetched_channels = record_extra.channels
        missing_channels = channels_to_fetch.difference(fetched_channels)
        if missing_channels:
            manifest = await ChannelManifest.get_most_recent_manifest()
            for missing_channel in missing_channels:
                if missing_channel in skip_functions:
                    message = "Function %s defined but cannot be evaluated for %s"
                    log.warning(message, missing_channel, record_id)
                elif missing_channel in manifest.channels:
                    message = "Channel %s does not have a value for %s"
                    log.warning(message, missing_channel, record_id)
                else:
                    message = "%s is not known as a channel or function name"
                    log.error(message, missing_channel)
                    raise FunctionParseError(message % missing_channel)

            return missing_channels

        for name, channel_value in fetched_channels.items():
            variable_data[name] = await Record._extract_variable(
                record_id=record_id,
                name=name,
                channel_value=channel_value,
                bit_depths=bit_depths,
            )

    @staticmethod
    async def _extract_variable(
        record_id: str,
        name: str,
        channel_value: PartialChannelModel,
        bit_depths: "list[int]",
    ) -> "np.ndarray | WaveformVariable | float":
        """
        Extracts and returns the relevant data from `channel_value`, handling
        extra calls needed for "image" and "waveform" types.
        """
        if hasattr(channel_value, "variable_value"):
            # Might be PartialImageVariableModel or PartialWaveformVariableChannelModel,
            # which store the value across function evaluations
            return channel_value.variable_value

        channel_dtype = await Record.get_channel_dtype(
            record_id=record_id,
            channel_name=name,
            channel_value=channel_value,
        )
        if channel_dtype == "image":
            raw_bit_depth = await Record.get_raw_bit_depth(
                record_id=record_id,
                channel_name=name,
                channel_value=channel_value,
            )
            if raw_bit_depth is not None:
                # Modify in place to store for each channel, getting around static func
                bit_depths.append(raw_bit_depth)

            image_bytes = await Image.get_image(
                record_id=record_id,
                channel_name=name,
                original_image=True,
                lower_level=0,
                upper_level=255,
                limit_bit_depth=8,  # Not relevant when `original_image=True`
                colourmap_name=None,
            )
            img_src = PILImage.open(image_bytes)
            img_array = np.array(img_src)
            return Record._bit_shift_to_raw(
                img_array=img_array,
                raw_bit_depth=raw_bit_depth,
            )

        elif channel_dtype == "waveform":
            x_units = getattr(channel_value.metadata, "x_units", None)
            waveform = Waveform.get_waveform(record_id, name)
            return WaveformVariable(waveform, x_units=x_units)
        else:
            return channel_value.data

    @staticmethod
    def _bit_shift_to_raw(
        img_array: np.ndarray,
        raw_bit_depth: "int | None",
    ) -> np.ndarray:
        """Shift the bits of a stored image back from most significant to original
        positions, so functions are applied to the raw pixel values.

        Args:
            img_array (np.ndarray): Stored image as a np.ndarray.
            raw_bit_depth (int | None): Original specified bit depth of the raw data.

        Returns:
            np.ndarray: Input image with the bits shifted to their original position.
        """
        if raw_bit_depth in (None, 8, 16):
            # If we don't know the original bit depth, or it exactly matches a
            # storage depth, no shift is possible/needed
            return img_array
        elif raw_bit_depth < 8:
            # Bit depths < 8 would have been stored as 8 bit, so shift back to raw
            return img_array / 2 ** (8 - raw_bit_depth)
        else:
            # Bit depths > 8 would have been stored as 16 bit, so shift back to raw
            return img_array / 2 ** (16 - raw_bit_depth)

    @staticmethod
    def _bit_shift_to_storage(
        img_array: np.ndarray,
        raw_bit_depth: "int | None",
    ) -> "tuple[np.ndarray, int]":
        """Shift the bits of a calculated image from numerically accurate positions to
        most significant bits for display/storage.

        Args:
            img_array (np.ndarray): Calculated image as a np.ndarray.
            raw_bit_depth (int | None): Original specified bit depth of the raw data.

        Returns:
            tuple[np.ndarray, int]:
                Input image with the bits shifted to storage/display positions,
                and the value of this storage bit depth.
        """
        if raw_bit_depth in (8, 16):
            # If bit depth exactly matches a storage depth, no shift is needed
            return img_array, raw_bit_depth
        elif raw_bit_depth < 8:
            # Bit depths < 8 would have been stored as 8 bit, so shift up to storage
            return img_array.astype(np.uint8) * 2 ** (8 - raw_bit_depth), 8
        else:
            # Bit depths > 8 would have been stored as 16 bit, so shift up to storage
            return img_array.astype(np.uint16) * 2 ** (16 - raw_bit_depth), 16

    @staticmethod
    def _parse_function_results(
        original_image: bool,
        lower_level: int,
        upper_level: int,
        limit_bit_depth: int,
        colourmap_name: str,
        result: "np.ndarray | WaveformVariable | np.float64",
        bit_depths: "list[int]",
        return_thumbnails: bool = True,
        truncate: bool = False,
    ) -> PartialVariableChannelModel:
        """
        Parses the numerical `result` and modifies `record` in place to contain
        the data in the expected format for the type of the `result`.
        """
        if isinstance(result, np.ndarray):
            return Record._parse_image_result(
                result=result,
                original_image=original_image,
                lower_level=lower_level,
                upper_level=upper_level,
                limit_bit_depth=limit_bit_depth,
                colourmap_name=colourmap_name,
                return_thumbnails=return_thumbnails,
                truncate=truncate,
                bit_depths=bit_depths,
            )

        elif isinstance(result, WaveformVariable):
            metadata = {"channel_dtype": "waveform"}
            if result.x_units is not None:
                metadata["x_units"] = result.x_units

            channel = PartialWaveformVariableChannelModel(
                metadata=metadata,
                variable_value=result,
            )
            if return_thumbnails:
                waveform = result.to_waveform()
                # Creating thumbnail takes ~ 0.05 s per waveform
                waveform.create_thumbnail()
                channel.thumbnail = waveform.thumbnail
            else:
                waveform_model = result.to_waveform_model()
                channel.data = waveform_model

            return channel

        else:
            metadata = {"channel_dtype": "scalar"}
            # Cannot return np.float64 as it can't be cast to JSON
            return PartialScalarChannelModel(metadata=metadata, data=float(result))

    @staticmethod
    def _parse_image_result(
        result: np.ndarray,
        original_image: bool,
        lower_level: int,
        upper_level: int,
        limit_bit_depth: int,
        colourmap_name: str,
        return_thumbnails: bool,
        truncate: bool,
        bit_depths: "list[int]",
    ) -> PartialImageVariableChannelModel:
        """Parses a numpy ndarray and returns image bytes, either for a thumbnail or
        full image.
        """
        if len(bit_depths) == 0:
            # We have no information about input bit depths, so set to max supported
            # This will not lose any information, but may make the image very dark
            overall_bit_depth = 16
        else:
            # Otherwise, take the highest depth encountered. There may be more than one
            # if the function depends on multiple channels with different depths,
            # in which case, we should try and store all information which means
            # choosing the highest bit depth needed
            overall_bit_depth = max(bit_depths)

        result, storage_bit_depth = Record._bit_shift_to_storage(
            img_array=result,
            raw_bit_depth=overall_bit_depth,
        )
        if return_thumbnails:
            metadata = {
                "channel_dtype": "image",
                "x_pixel_size": result.shape[1],
                "y_pixel_size": result.shape[0],
            }

            # In each dimension, determine the number of pixels in the original
            # that need to map onto one pixel in the thumbnail
            thumbnail_x_size = Config.config.images.thumbnail_size[0]
            thumbnail_y_size = Config.config.images.thumbnail_size[1]
            step_x = result.shape[1] // thumbnail_x_size
            step_y = result.shape[0] // thumbnail_y_size

            # Slice with a step size that downsamples to the thumbnails shape
            image_array = result[::step_y, ::step_x]
            image_bytes = FalseColourHandler.apply_false_colour(
                image_array=image_array,
                storage_bit_depth=storage_bit_depth,
                lower_level=lower_level,
                upper_level=upper_level,
                limit_bit_depth=limit_bit_depth,
                colourmap_name=colourmap_name,
            )
            image_bytes.seek(0)
            image_b64 = base64.b64encode(image_bytes.getvalue())

            return PartialImageVariableChannelModel(
                metadata=metadata,
                variable_value=result,
                thumbnail=Record.truncate_bytes(truncate, image_b64),
            )

        else:
            if original_image:
                image_bytes = BytesIO()
                img_temp = PILImage.fromarray(result.astype(np.int32))
                img_temp.save(image_bytes, format="PNG")
            else:
                image_bytes = FalseColourHandler.apply_false_colour(
                    image_array=result,
                    storage_bit_depth=storage_bit_depth,
                    lower_level=lower_level,
                    upper_level=upper_level,
                    limit_bit_depth=limit_bit_depth,
                    colourmap_name=colourmap_name,
                )

            return PartialImageVariableChannelModel(
                data=image_bytes.getvalue(),
                variable_value=result,
            )

    @staticmethod
    def truncate_bytes(truncate: bool, image_b64: bytes) -> bytes:
        """Utility function for optionally truncating bytes for testing."""
        if truncate:
            return image_b64[:50]
        else:
            return image_b64
