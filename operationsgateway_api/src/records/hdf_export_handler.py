from datetime import datetime, timezone
from io import BytesIO
import logging
from typing import Any, List

import h5py
import numpy as np
from PIL import Image as PILImage

from operationsgateway_api.src.exceptions import ExportError
from operationsgateway_api.src.functions.variable_transformer import VariableTransformer
from operationsgateway_api.src.models import (
    ChannelDtype,
    ChannelManifestModel,
    PartialChannels,
    PartialRecordModel,
)
from operationsgateway_api.src.records.export_handler import ExportHandler
from operationsgateway_api.src.records.record import Record

log = logging.getLogger()


class HdfExportHandler(ExportHandler):
    """
    Exports the records to a single HDF5 file, using the fetching in `ExportHandler`
    but writing to the file in `_write_to_zip` and `_process_data_channel`.
    """

    return_raw_bit_depth = True

    def __init__(
        self,
        records_data: list[PartialRecordModel],
        channel_manifest: ChannelManifestModel,
        projection: List[str],
        functions: "list[dict[str, str]]",
    ) -> None:
        """
        Exports every channel as the original data, with no false colour and no
        rendered waveform or vector images.
        """
        super().__init__(
            records_data=records_data,
            channel_manifest=channel_manifest,
            projection=projection,
            lower_level=0,
            upper_level=255,
            limit_bit_depth=8,
            colourmap_name=None,
            functions=functions,
            export_scalars=True,
            export_strings=True,
            export_images=True,
            export_image_series=True,
            export_float_images=True,
            export_waveform_csvs=True,
            export_waveform_images=False,
            export_vector_csvs=True,
            export_vector_images=False,
        )
        self.hdf_file_in_memory = BytesIO()
        self.hdf_file = None
        self.records_by_id = {}
        self.function_expressions = {}
        self.size_exceeded = False

    @staticmethod
    def get_projection(projection: List[str]) -> List[str]:
        """
        Returns `metadata`, and the `metadata`, `data` and `shape` of each channel in
        `projection`.
        """
        hdf_projection = ["metadata"]
        for proj in projection:
            projection_parts = proj.split(".")
            if projection_parts[0] == "channels" and len(projection_parts) > 1:
                for field in ("metadata", "data", "shape"):
                    path = f"channels.{projection_parts[1]}.{field}"
                    if path not in hdf_projection:
                        hdf_projection.append(path)

        return hdf_projection

    def get_export_file_bytes(self) -> BytesIO:
        """Returns the HDF file."""
        return self.hdf_file_in_memory

    async def _init_function_types(self) -> None:
        """
        Gets the function types, then removes the functions that don't return a
        scalar, waveform or image from `functions`, adding an error message for each.
        """
        await super()._init_function_types()
        supported = []
        for function in self.functions:
            name = function["name"]
            function_type = self.function_types[name]
            if function_type in ("scalar", "waveform", "image"):
                supported.append(function)
            else:
                self.errors_file_in_memory.write(
                    f"Could not export function {name}: functions that return "
                    f"{function_type} are not supported\n",
                )

        self.functions = supported

    def _start_export(self) -> None:
        """
        Opens `hdf_file` on `hdf_file_in_memory` and creates a group for each record,
        with the record metadata as attributes.
        """
        self.records_by_id = {record.id_: record for record in self.records_data}
        self.function_expressions = {
            function["name"]: function["expression"]
            for function in self.functions or []
        }
        self.hdf_file = h5py.File(self.hdf_file_in_memory, "w")
        for record in self.records_data:
            group = self.hdf_file.create_group(self._get_group_name(record.id_))
            if record.metadata is not None:
                self._write_attributes(group, record.metadata.model_dump())

    def _finish_export(self) -> None:
        """
        Writes the lines of `errors_file_in_memory` to an `EXPORT_ERRORS` dataset, if
        there are any, then closes `hdf_file`. Raises an `ExportError` if `_check_size`
        found the file to be over `max_filesize_bytes`. It is raised here because this
        runs after the tasks, so it is not wrapped in an `ExceptionGroup`.
        """
        errors = self.errors_file_in_memory.getvalue().splitlines()
        if errors and not self.size_exceeded:
            self.hdf_file.create_dataset(
                "EXPORT_ERRORS",
                data=np.array(errors, dtype=h5py.string_dtype()),
            )

        self.hdf_file.close()
        if self.size_exceeded:
            raise ExportError(
                "Too much data requested. Reduce either the number of records or "
                "channels requested, or both. The skip and limit parameters can also "
                "be used to export the records in pages.",
            )

    async def _process_data_channel(
        self,
        channels: PartialChannels,
        record_id: str,
        raw_data: dict[str, Any],
        channel_name: str,
        line: str,
    ) -> str:
        """
        Writes scalar and string channels, otherwise calls `_process_data_channel` in
        `ExportHandler`. Then calls `_check_size`. Does nothing once `size_exceeded`
        is set, so the remaining channels are not fetched.
        """
        if self.size_exceeded:
            return line

        if self._get_channel_type(channel_name) in ("scalar", "string"):
            value = channels[channel_name].data if channel_name in channels else None
            if value is not None:
                self._write_to_hdf(record_id, channel_name, {"data": value})
        else:
            line = await super()._process_data_channel(
                channels,
                record_id,
                raw_data,
                channel_name,
                line,
            )

        self._check_size()
        return line

    async def _write_to_zip(
        self,
        record_id: str,
        channel_name: str,
        extension: str,
        data: str | bytes,
    ) -> None:
        """
        Writes the channel to the HDF file instead of the zip file. `data` is a png, npy
        or npz file for an image, image series or float image, and a CSV file for a
        waveform or vector. A function image is written from the array it was
        calculated as, and has a `bit_depth` of the largest of the images it uses.
        """
        channel = self.records_by_id[record_id].channels[channel_name]
        channel_type = self._get_channel_type(channel_name)
        attributes = {}

        if channel_name in self.function_expressions and channel_type == "image":
            datasets = {"data": channel.variable_value}
            bit_depth = self._get_function_bit_depth(record_id, channel_name)
            attributes = {
                "bit_depth": bit_depth or 16,
                "bit_depth_inferred": not bit_depth,
            }
        elif extension == "csv":
            rows = [line.split(",") for line in data.splitlines()]
            if channel_type == "waveform":
                xy = np.array(rows, dtype=np.float64).reshape(-1, 2)
                datasets = {"x": xy[:, 0], "y": xy[:, 1]}
            else:
                values = [row[-1] for row in rows]
                datasets = {"data": np.array(values, dtype=np.float64)}
        elif extension == "npz":
            with np.load(BytesIO(data)) as npz_file:
                datasets = {"data": npz_file["arr_0"]}
        else:
            if extension == "png":
                with PILImage.open(BytesIO(data)) as png:
                    array = np.array(png)
            else:
                array = np.load(BytesIO(data))
            # Shift back to the ingested values, which are stored as most significant
            # bits, and cast back to the stored dtype as the shift returns floats
            bit_depth = getattr(channel.metadata, "bit_depth", None)
            raw_array = Record._bit_shift_to_raw(array, bit_depth)
            datasets = {"data": raw_array.astype(array.dtype, copy=False)}

        self._write_to_hdf(record_id, channel_name, datasets, attributes)

    def _write_to_hdf(
        self,
        record_id: str,
        channel_name: str,
        datasets: dict[str, Any],
        attributes: dict[str, Any] | None = None,
    ) -> None:
        """
        Writes a group for the channel in the record's group, with the attributes
        `channel_dtype`, `expression` (for functions), the channel metadata and
        `attributes`, and a dataset for each item in `datasets`.
        """
        record_group = self.hdf_file[self._get_group_name(record_id)]
        if channel_name in record_group:
            return

        channel = self.records_by_id[record_id].channels[channel_name]
        channel_type = ChannelDtype(self._get_channel_type(channel_name))
        channel_group = record_group.create_group(channel_name)
        channel_group.attrs["channel_dtype"] = channel_type.value
        if channel_name in self.function_expressions:
            channel_group.attrs["expression"] = self.function_expressions[channel_name]

        # channel_dtype is written above, and float images have no bit depth
        skipped = {"channel_dtype"}
        if channel_type == ChannelDtype.FLOAT_IMAGE:
            skipped.update(("bit_depth", "bit_depth_inferred"))
        if channel.metadata is not None:
            metadata = channel.metadata.model_dump()
            self._write_attributes(channel_group, metadata, skipped)
        self._write_attributes(channel_group, attributes or {})

        for name, data in datasets.items():
            channel_group.create_dataset(name, data=data)

    def _write_attributes(
        self,
        group: h5py.Group,
        attributes: dict[str, Any],
        skipped: set[str] = frozenset(),
    ) -> None:
        """
        Writes `attributes` to `group` with `_to_attribute`, leaving out the names in
        `skipped` and the values that are `None` or an empty string.
        """
        for name, value in attributes.items():
            if name not in skipped and value is not None and value != "":
                group.attrs[name] = self._to_attribute(value)

    def _get_function_bit_depth(self, record_id: str, function_name: str) -> int | None:
        """
        Returns the largest `bit_depth` of the channels in the function's expression,
        or None if none of them have one.
        """
        transformer = VariableTransformer()
        transformer.evaluate(self.function_expressions[function_name])
        channels = self.records_by_id[record_id].channels
        bit_depths = [
            getattr(channels[variable].metadata, "bit_depth", None)
            for variable in transformer.variables
            if variable in channels
        ]
        bit_depths = [bit_depth for bit_depth in bit_depths if bit_depth]
        return max(bit_depths) if bit_depths else None

    def _get_group_name(self, record_id: str) -> str:
        """Returns the shot number if `shotnum_naming` is set, otherwise `record_id`."""
        return (
            self._filename_identifier(record_id) if self.shotnum_naming else record_id
        )

    def _check_size(self) -> None:
        """
        Flushes `hdf_file` so that everything written so far is in
        `hdf_file_in_memory`, then sets `size_exceeded` if that is over
        `max_filesize_bytes`. It doesn't raise, because an exception in a task is
        wrapped in an `ExceptionGroup`, and the image, image series and float image
        methods catch every exception.
        """
        self.hdf_file.flush()
        nbytes = self.hdf_file_in_memory.getbuffer().nbytes
        log.info("HDF file size: %d", nbytes)
        if nbytes > ExportHandler.max_filesize_bytes:
            self.size_exceeded = True

    @staticmethod
    def _to_attribute(value: Any) -> Any:
        """
        Returns `value` in a form h5py can store as an attribute: datetimes as ISO 8601
        strings in UTC (timezone-naive datetimes are taken to be UTC), lists as arrays
        of strings, other bool, int, float and str values as they are, and anything
        else as a string.
        """
        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc).isoformat(timespec="milliseconds")

        if isinstance(value, list):
            return np.array([str(item) for item in value], dtype=h5py.string_dtype())

        if isinstance(value, bool | int | float | str):
            return value

        return str(value)
