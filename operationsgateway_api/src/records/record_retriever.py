import asyncio
from io import BytesIO
import logging

import numpy as np
from PIL import Image as PILImage

from operationsgateway_api.src.channels.channel_manifest import ChannelManifest
from operationsgateway_api.src.exceptions import FunctionParseError
from operationsgateway_api.src.functions.expression_transformer import (
    ExpressionTransformer,
)
from operationsgateway_api.src.functions.variable_models import WaveformVariable
from operationsgateway_api.src.functions.variable_transformer import VariableTransformer
from operationsgateway_api.src.models import PartialRecordModel
from operationsgateway_api.src.records.image import Image
from operationsgateway_api.src.records.record import Record
from operationsgateway_api.src.records.waveform import Waveform


log = logging.getLogger()


class FunctionData:
    """
    Utility class to hold the data associated with a single function during evaluation.
    """

    def __init__(self, function: dict[str, str]):
        self.name = function["name"]
        self.expression = function["expression"]
        self.variable_transformer = VariableTransformer()
        self.variable_transformer.evaluate(self.expression)

    def get_bit_depths(self, all_bit_depths: dict[str, int]) -> list[int]:
        """
        Input image data has a defined bit depth. In principle a function may depend on
        multiple images with different depths. To allow us to determine the appropriate
        output bit depth, get the depths relevant to this function from a dictionary of
        all the depths.
        """
        relevant_bit_depths = []
        for variable in self.variable_transformer.variables:
            if variable in all_bit_depths:
                relevant_bit_depths.append(all_bit_depths[variable])

        return relevant_bit_depths


class RecordRetriever:
    """
    Applies business logic for processing retrieved records. Primarily, this relates to
    functions.
    """

    def __init__(
        self,
        record: PartialRecordModel,
        functions: list[dict[str, str]],
        original_image: bool,
        lower_level: int = 0,
        upper_level: int = 255,
        limit_bit_depth: int = 8,
        colourmap_name: str | None = None,
        float_colourmap_name: str | None = None,
        vector_skip: int | None = None,
        vector_limit: int | None = None,
        return_thumbnails: bool = True,
        truncate: bool = False,
    ) -> None:
        # Request parameters and the record as is from the database
        self.record = record
        self.original_image = original_image
        self.lower_level = lower_level
        self.upper_level = upper_level
        self.limit_bit_depth = limit_bit_depth
        self.colourmap_name = colourmap_name
        self.float_colourmap_name = float_colourmap_name
        self.vector_skip = vector_skip
        self.vector_limit = vector_limit
        self.return_thumbnails = return_thumbnails
        self.truncate = truncate

        # Functions specific objects
        self.functions_data = [FunctionData(f) for f in functions] if functions else []
        self.coroutines = []
        self.variable_data = {}
        self.raw_data = {}
        # Named in the manifest, but not defined for the record
        self.undefined_channels = set()
        # Not named in the manifest, could be another function name
        self.unknown_variables = set()
        self.bit_depths = {}
        self._manifest_channel_names = None

    async def process_record(self):
        """
        Apply all relevant processing to a retrieved record: false colour, truncating,
        and applying functions.
        """
        if self.record.channels:
            await Record.apply_false_colour_to_thumbnails(
                self.record,
                self.lower_level,
                self.upper_level,
                self.colourmap_name,
                self.float_colourmap_name,
                vector_skip=self.vector_skip,
                vector_limit=self.vector_limit,
            )

            if self.truncate:
                Record.truncate_thumbnails(self.record)

        if self.functions_data:
            await self.process_functions()

    async def process_functions(self) -> None:
        """
        Processes functions by identifying and fetching all required channels from the
        database, then concurrently fetching the actual data from storage, and finally
        evaluating the actual expressions.
        """
        if self.record.channels is None:
            self.record.channels = {}

        # Identify channels we need to fetch
        all_variables = set()
        projection = set()
        tasks = []
        for function_data in self.functions_data:
            for variable in function_data.variable_transformer.variables:
                all_variables.add(variable)
                if variable not in self.record.channels:
                    projection.add(f"channels.{variable}")

        # Get metadata for any channels not already in the record
        if projection:
            record_extra = await Record.find_record_by_id(
                self.record.id_,
                {},
                projection,
            )
            if record_extra.channels is not None:
                self.record.channels.update(record_extra.channels)

        # Build and execute a list of coroutines to fetch the data concurrently
        for variable in all_variables:
            await self._extract_variable(variable)

        async with asyncio.TaskGroup() as task_group:
            for coroutine in self.coroutines:
                task = task_group.create_task(coroutine)
                tasks.append(task)

        # Finally, evaluate the expressions and extract the results
        expression_transformer = ExpressionTransformer(channels=self.variable_data)
        for function_data in self.functions_data:
            undefined = function_data.variable_transformer.variables.intersection(
                self.undefined_channels,
            )
            if undefined:
                # This is OK, not all records have all channels defined
                # continue gracefully
                message = "Channel/functions %s undefined for %s"
                log.warning(message, undefined, self.record.id_)
                if function_data.name in self.unknown_variables:
                    # Mark this function as undefined, rather than unknown, in case
                    # another function depends on it
                    self.undefined_channels.add(function_data.name)
                    self.unknown_variables.remove(function_data.name)

                continue

            unknown = function_data.variable_transformer.variables.intersection(
                self.unknown_variables,
            )
            if unknown:
                # This is not OK, as it is either not a real channel/function name or
                # indicates a circular dependency which cannot be evaluated
                log.error("%s are not recognised channels/functions", unknown)
                msg = f"{unknown} are not recognised channels/functions"
                raise FunctionParseError(msg)

            result = expression_transformer.evaluate(function_data.expression)
            self.variable_data[function_data.name] = result
            if function_data.name in self.unknown_variables:
                self.unknown_variables.remove(function_data.name)

            self.record.channels[function_data.name] = Record._parse_function_results(
                original_image=self.original_image,
                lower_level=self.lower_level,
                upper_level=self.upper_level,
                limit_bit_depth=self.limit_bit_depth,
                colourmap_name=self.colourmap_name,
                result=result,
                bit_depths=function_data.get_bit_depths(self.bit_depths),
                return_thumbnails=self.return_thumbnails,
                truncate=self.truncate,
            )

        self.record.channels = self.record.channels

    async def _extract_variable(self, variable: str) -> None:
        """
        Depending on the channel type, add the coroutine to fetch the data to `self`.
        Scalar channels can be extracted now, and missing channels are recorded.
        """
        if variable in self.record.channels:
            channel_dtype = await Record.get_channel_dtype(
                record_id=self.record.id_,
                channel_name=variable,
                channel_value=self.record.channels[variable],
            )
            if channel_dtype == "image":
                raw_bit_depth = await Record.get_raw_bit_depth(
                    record_id=self.record.id_,
                    channel_name=variable,
                    channel_value=self.record.channels[variable],
                )
                if raw_bit_depth is not None:
                    self.bit_depths[variable] = raw_bit_depth

                coroutine = self._get_image_variable(
                    self.record.id_,
                    variable,
                    raw_bit_depth,
                )
                self.coroutines.append(coroutine)

            elif channel_dtype == "waveform":
                coroutine = self._get_waveform_variable(
                    self.record.id_,
                    variable,
                    getattr(self.record.channels[variable].metadata, "x_units", None),
                )
                self.coroutines.append(coroutine)

            else:
                self.variable_data[variable] = self.record.channels[variable].data
        elif variable in await self._get_channel_manifest():
            self.undefined_channels.add(variable)
        else:
            self.unknown_variables.add(variable)

    async def _get_image_variable(
        self,
        record_id: str,
        channel_name: str,
        raw_bit_depth: int,
    ) -> None:
        """Coroutine to fetch image data."""
        image_bytes = await Image.get_image(
            record_id=record_id,
            channel_name=channel_name,
            original_image=True,
            lower_level=0,
            upper_level=255,
            limit_bit_depth=8,  # Not relevant when `original_image=True`
            colourmap_name=None,
        )
        self.raw_data[channel_name] = image_bytes

        img_src = PILImage.open(BytesIO(image_bytes))
        img_array = np.array(img_src)
        variable_value = Record._bit_shift_to_raw(
            img_array=img_array,
            raw_bit_depth=raw_bit_depth,
        )
        self.variable_data[channel_name] = variable_value

    async def _get_waveform_variable(
        self,
        record_id: str,
        channel_name: str,
        x_units: str,
    ) -> None:
        """Coroutine to fetch Waveform data."""
        waveform = await Waveform.get_waveform(record_id, channel_name)
        self.raw_data[channel_name] = waveform
        self.variable_data[channel_name] = WaveformVariable(waveform, x_units=x_units)

    async def _get_channel_manifest(self) -> set[str]:
        if self._manifest_channel_names is None:
            manifest = await ChannelManifest.get_most_recent_manifest()
            self._manifest_channel_names = set(manifest.channels.keys())

        return self._manifest_channel_names
