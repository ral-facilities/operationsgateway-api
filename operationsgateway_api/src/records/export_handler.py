import asyncio
from io import BytesIO, StringIO
import logging
from typing import Any, List, Tuple, Union
import zipfile

from operationsgateway_api.src.config import Config
from operationsgateway_api.src.exceptions import ExportError
from operationsgateway_api.src.functions.type_transformer import TypeTransformer
from operationsgateway_api.src.models import (
    ChannelDtype,
    ChannelManifestModel,
    PartialChannels,
    PartialRecordModel,
    PartialWaveformChannelModel,
    WaveformChannelMetadataModel,
    WaveformModel,
)
from operationsgateway_api.src.records.float_image import FloatImage
from operationsgateway_api.src.records.image import Image
from operationsgateway_api.src.records.record_retriever import RecordRetriever
from operationsgateway_api.src.records.vector import Vector
from operationsgateway_api.src.records.waveform import Waveform


log = logging.getLogger()


class ExportHandler:
    max_filesize_bytes = Config.config.export.max_filesize_bytes

    def __init__(
        self,
        records_data: list[PartialRecordModel],
        channel_manifest: ChannelManifestModel,
        projection: List[str],
        lower_level: int,
        upper_level: int,
        limit_bit_depth: int,
        colourmap_name: str,
        functions: "list[dict[str, str]]",
        export_scalars: bool,
        export_images: bool,
        export_float_images: bool,
        export_waveform_csvs: bool,
        export_waveform_images: bool,
        export_vector_csvs: bool,
        export_vector_images: bool,
    ) -> None:
        """
        Store all of the information that needs to be processed during the export
        """
        self.records_data = records_data
        self.channel_manifest = channel_manifest
        self.projection = projection
        self.lower_level = lower_level
        self.upper_level = upper_level
        self.limit_bit_depth = limit_bit_depth
        self.colourmap_name = colourmap_name
        self.export_scalars = export_scalars
        self.export_images = export_images
        self.export_float_images = export_float_images
        self.export_waveform_csvs = export_waveform_csvs
        self.export_waveform_images = export_waveform_images
        self.export_vector_csvs = export_vector_csvs
        self.export_vector_images = export_vector_images

        self.record_ids = []
        self.errors_file_in_memory = StringIO()
        self.main_csv_file_in_memory = StringIO()
        self.zip_file_in_memory = BytesIO()
        self.zip_file = zipfile.ZipFile(
            self.zip_file_in_memory,
            "a",
            zipfile.ZIP_DEFLATED,
            False,
        )
        self.zip_lock = asyncio.Lock()

        self.functions = functions
        self.function_types = {}

    @staticmethod
    def _ensure_waveform_metadata(channel: PartialWaveformChannelModel) -> None:
        """Utility method for ensuring Waveform Metadata and units are not None."""
        if channel.metadata is None:
            channel.metadata = WaveformChannelMetadataModel(x_units="", y_units="")
        else:
            if channel.metadata.x_units is None:
                channel.metadata.x_units = ""
            if channel.metadata.y_units is None:
                channel.metadata.y_units = ""

    @property
    def original_image(self) -> bool:
        """If none of the false colour parameters are set then the original
        image is required.
        """
        return (
            self.lower_level == 0
            and self.upper_level == 255
            and self.limit_bit_depth == 8
            and self.colourmap_name is None
        )

    # NOTE: needs to be async as it is calling async methods to get image and waveform
    # files from disk
    async def process_records(self) -> None:
        """
        Loop through the records creating a main CSV file from the scalar values and
        adding image and waveform files to a zip file ready for download. If no image
        or waveform channels are requested then just the main CSV file will be returned
        otherwise all files will be put into a zip file.
        """
        if self.functions:
            await self._init_function_types()

        self._create_main_csv_headers()
        tasks = []
        async with asyncio.TaskGroup() as task_group:
            for record_data in self.records_data:
                task = task_group.create_task(self._process_record(record_data))
                tasks.append(task)

        for task in tasks:
            line = task.result()
            # don't put empty lines in the CSV file
            if line != "":
                self.main_csv_file_in_memory.write(line + "\n")

        self._add_main_csv_file_to_zip()
        self._add_messages_file_to_zip()

        # end of adding files to the zip file
        # close the file to finish writing the directory entry etc.
        self.zip_file.close()

    async def _init_function_types(self):
        """Before writing the CSV header, need to determine function return types so
        that any scalar functions can be included as columns.
        """
        transformer = TypeTransformer()
        for function_dict in self.functions:
            name = function_dict["name"]
            expression = function_dict["expression"]
            self.function_types[name] = await transformer.evaluate(name, expression)

    def _create_main_csv_headers(self) -> None:
        """
        Process the "projection" (data table columns requested) to add the necessary
        column headings to the main CSV file.
        projection will be an array like:
        ["metadata.shotnum", "channels.N_COMP_NF_IMAGE..."]
        where the column/data channel name will be the part between the first and
        second dots eg. shotnum and N_COMP_NF_IMAGE in these examples.
        """
        line = ""
        for proj in self.projection:
            channel_name = self._get_channel_name(proj)
            if proj.split(".")[0] == "channels":
                # image and waveform data will be exported to separate files so will not
                # have values put in the main csv file
                channel_type = self._get_channel_type(channel_name)
                if channel_type not in ["image", "float_image", "waveform", "vector"]:
                    line = self._add_value_to_csv_line(line, channel_name)
            else:
                # this must be a "metadata" channel
                line = self._add_value_to_csv_line(line, channel_name)
        # don't put empty lines in the CSV file
        if line != "":
            self.main_csv_file_in_memory.write(line + "\n")

    def _get_channel_name(self, projection) -> str:
        """
        Get the name of the channel from the search projection
        """
        if projection == "_id":
            # this is a special case
            return "ID"
        else:
            projection_parts = projection.split(".")
            if len(projection_parts) < 2:
                message = f"Projection '{projection}' did not include a second term"
                raise ExportError(message)

            return projection_parts[1]

    def _get_channel_type(self, channel_name: str) -> ChannelDtype:
        """Extracts the "type" for either a function or channel."""
        if channel_name in self.function_types:
            return self.function_types[channel_name]
        elif channel_name in self.channel_manifest.channels:
            return self.channel_manifest.channels[channel_name].type_
        else:
            message = f"'{channel_name}' is not a recognised channel or function name"
            raise ExportError(message)

    async def _process_record(self, record_data: PartialRecordModel) -> str:
        """
        Process an individual record asynchronously. If functions are defined, these are
        evaluated first. Any channels fetched as part of this are stored, and re-used
        if present in self.projection to reduce the number of requests. Each projection
        for this record is handled concurrently.
        """
        record_id = record_data.id_
        self.record_ids.append(record_id)
        raw_data = {}
        if self.functions:
            record_retriever = RecordRetriever(
                record=record_data,
                functions=self.functions,
                original_image=self.original_image,
                lower_level=self.lower_level,
                upper_level=self.upper_level,
                limit_bit_depth=self.limit_bit_depth,
                colourmap_name=self.colourmap_name,
                return_thumbnails=False,
            )
            await record_retriever.process_functions()
            raw_data = record_retriever.raw_data

        line = ""
        tasks = []
        async with asyncio.TaskGroup() as task_group:
            for proj in self.projection:
                coroutine = self._process_projection(record_data, raw_data, proj)
                task = task_group.create_task(coroutine)
                tasks.append(task)

        for task in tasks:
            line += task.result()

        return line

    async def _process_projection(
        self,
        record_data: PartialRecordModel,
        raw_data: dict[str, BytesIO | WaveformModel],
        proj: str,
    ) -> str:
        """
        Asynchronously process a single projection. This may be metadata or may be
        channel data which needs to be fetched, taking a non-trivial amount of time.
        """
        projection_parts = proj.split(".")
        if proj == "_id":
            return self._add_value_to_csv_line(
                line="",
                value=record_data.id_,
                verbose=True,
            )
        elif projection_parts[0] == "metadata":
            return self._add_value_to_csv_line(
                line="",
                value=getattr(record_data.metadata, projection_parts[1], ""),
                verbose=True,
            )
        elif projection_parts[0] == "channels":
            # process one of the data channels
            return await self._process_data_channel(
                record_data.channels,
                record_data.id_,
                raw_data,
                projection_parts[1],
                "",
            )
        else:
            log.warning(
                "Unrecognised first projection part: %s",
                projection_parts[0],
            )
            return ""

    async def _process_data_channel(
        self,
        channels: PartialChannels,
        record_id: str,
        raw_data: dict[str, BytesIO | WaveformModel],
        channel_name: str,
        line: str,
    ) -> str:
        """
        Process data channels (those whose "projection" starts with "channels." as
        opposed to metadata channels whose projection starts with "metadata.") by
        adding image and waveform files to a zip file and scalar data to a line of text
        that will be added to the main CSV file.
        """
        # process an image channel
        channel_type = self._get_channel_type(channel_name)
        if channel_type == "image":
            log.info("Channel %s is an image", channel_name)
            await self._add_image_to_zip(channels, record_id, raw_data, channel_name)
        elif channel_type == "float_image":
            log.info("Channel %s is a float image", channel_name)
            await self._add_float_image_to_zip(channels, record_id, channel_name)
        # process a waveform channel
        elif channel_type == "waveform":
            log.info("Channel %s is a waveform", channel_name)
            await self._add_waveform_to_zip(channels, record_id, raw_data, channel_name)
        elif channel_type == "vector":
            log.info("Channel %s is a vector", channel_name)
            await self._add_vector_to_zip(channels, record_id, channel_name)
        # process a scalar channel
        else:
            log.info("Channel %s is a scalar", channel_name)
            if channel_name in channels and channels[channel_name].data is not None:
                value = channels[channel_name].data
            else:
                value = ""
            line = self._add_value_to_csv_line(line=line, value=value, verbose=True)
        return line

    async def _add_image_to_zip(
        self,
        channels: PartialChannels,
        record_id: str,
        raw_data: dict[str, BytesIO],
        channel_name: str,
    ) -> None:
        """
        Get an image from disk (Echo) and add it to the zip file being created for
        download.
        Note that although there is no specific requirement for it, the export
        functionality supports the export of colour mapped images. As well as
        mirroring the signature of the /records endpoint, the get_image() function
        supports this so it is easy to pass the false colour parameters on if they are
        specified. If none of them are specified the original image is used.
        """
        if not self.export_images or channel_name not in channels:
            return

        log.info("Getting image to add to zip: %s %s", record_id, channel_name)
        try:
            if channel_name in self.function_types:
                image_bytes = channels[channel_name].data
            elif channel_name in raw_data:
                if self.original_image:
                    image_bytes = raw_data[channel_name]
                else:
                    image_bytes = Image.apply_false_colour(
                        image_bytes=raw_data[channel_name],
                        original_image=self.original_image,
                        lower_level=self.lower_level,
                        upper_level=self.upper_level,
                        limit_bit_depth=self.limit_bit_depth,
                        colourmap_name=self.colourmap_name,
                    )
            else:
                image_bytes = await Image.get_image(
                    record_id=record_id,
                    channel_name=channel_name,
                    original_image=self.original_image,
                    lower_level=self.lower_level,
                    upper_level=self.upper_level,
                    limit_bit_depth=self.limit_bit_depth,
                    colourmap_name=self.colourmap_name,
                )
            await self._write_to_zip(f"{record_id}_{channel_name}.png", image_bytes)
            self._check_zip_file_size()
        except Exception:
            log.exception("Could not find image for %s %s", record_id, channel_name)
            self.errors_file_in_memory.write(
                f"Could not find image for {record_id} {channel_name}\n",
            )

    async def _add_float_image_to_zip(
        self,
        channels: PartialChannels,
        record_id: str,
        channel_name: str,
    ) -> None:
        """
        Get a float image from Echo and add it to the zip file being created for
        download.
        """
        if not self.export_float_images or channel_name not in channels:
            return

        log.info("Getting float image to add to zip: %s %s", record_id, channel_name)
        try:
            storage_bytes = await FloatImage.get_bytes(record_id, channel_name)
            await self._write_to_zip(f"{record_id}_{channel_name}.npz", storage_bytes)
            self._check_zip_file_size()
        except Exception:
            self.errors_file_in_memory.write(
                f"Could not find float image for {record_id} {channel_name}\n",
            )

    async def _add_waveform_to_zip(
        self,
        channels: PartialChannels,
        record_id: str,
        raw_data: dict[str, WaveformModel],
        channel_name: str,
    ) -> None:
        """
        Get the arrays of x and y values for a waveform and then either write them to a
        CSV file or create a rendered image of the waveform (or both) and add the
        created file(s) to the zip file being created ready for download.
        """
        export_waveforms = self.export_waveform_csvs or self.export_waveform_images
        if not export_waveforms or channel_name not in channels:
            return

        log.info(
            "Getting waveform to add to zip: %s %s",
            record_id,
            channel_name,
        )
        channel = channels[channel_name]
        ExportHandler._ensure_waveform_metadata(channel)
        try:
            if channel_name in self.function_types:
                waveform_model = channel.data
            elif channel_name in raw_data:
                waveform_model = raw_data[channel_name]
            else:
                waveform_model = await Waveform.get_waveform(record_id, channel_name)
        except Exception:
            self.errors_file_in_memory.write(
                f"Could not find waveform for {record_id} {channel_name}\n",
            )
            # no point trying to process the waveform so return at this point
            return

        if self.export_waveform_csvs:
            num_points = len(waveform_model.x)
            waveform_csv_in_memory = StringIO()
            for point_num in range(num_points):
                waveform_csv_in_memory.write(
                    str(waveform_model.x[point_num])
                    + ","
                    + str(waveform_model.y[point_num])
                    + "\n",
                )
            csv_bytes = waveform_csv_in_memory.getvalue()
            await self._write_to_zip(f"{record_id}_{channel_name}.csv", csv_bytes)
            self._check_zip_file_size()

        if self.export_waveform_images:
            # if rendered trace images have been requested then add those
            waveform = Waveform(waveform_model)
            png_bytes = waveform.get_fullsize_png(
                x_label=channel.metadata.x_units,
                y_label=channel.metadata.y_units,
            )
            await self._write_to_zip(f"{record_id}_{channel_name}.png", png_bytes)
            self._check_zip_file_size()

    async def _add_vector_to_zip(
        self,
        channels: PartialChannels,
        record_id: str,
        channel_name: str,
    ) -> None:
        """
        Get vector data from echo and add it to the zip file in CSV or PNG form.
        """
        export_vectors = self.export_vector_csvs or self.export_vector_images
        if not export_vectors or channel_name not in channels:
            return

        channel = channels[channel_name]
        labels = None
        if channel.metadata and channel.metadata.labels:
            labels = channel.metadata.labels

        log.info(
            "Getting vector to add to zip: %s %s",
            record_id,
            channel_name,
        )
        try:
            vector_model = await Vector.get_vector(record_id, channel_name)
        except Exception:
            self.errors_file_in_memory.write(
                f"Could not find vector for {record_id} {channel_name}\n",
            )
            # no point trying to process the vector so return at this point
            return

        if self.export_vector_csvs:
            string_io = StringIO()
            if labels:
                for label, value in zip(labels, vector_model.data, strict=True):
                    string_io.write(f"{label},{value}\n")
            else:
                for value in vector_model.data:
                    string_io.write(f"{value}\n")

            data = string_io.getvalue()
            await self._write_to_zip(f"{record_id}_{channel_name}.csv", data)
            self._check_zip_file_size()

        if self.export_vector_images:
            vector = Vector(vector_model)
            vector_image = vector.get_fullsize_png(labels)
            await self._write_to_zip(f"{record_id}_{channel_name}.png", vector_image)
            self._check_zip_file_size()

    def _add_main_csv_file_to_zip(self):
        """
        If other files have been exported and therefore a zip file is being prepared
        for export then add the CSV file to the zip file.
        """
        if self.export_scalars:
            if (
                len(self.zip_file.infolist()) > 0
                and len(self.main_csv_file_in_memory.getvalue()) > 0
            ):
                self.zip_file.writestr(
                    f"{self.get_filename_stem()}.csv",
                    self.main_csv_file_in_memory.getvalue(),
                )
                self._check_zip_file_size()

    def _add_messages_file_to_zip(self):
        """
        Add a file listing any errors that might be useful to the user to the zip such
        as any files or waveforms that were not found.
        """
        errors_str = self.errors_file_in_memory.getvalue()
        if len(errors_str) > 0:
            self.zip_file.writestr(
                "EXPORT_ERRORS.txt",
                errors_str,
            )
            log.error("Returning export errors file containing: \n%s", errors_str)

    def get_export_file_bytes(self) -> Union[BytesIO, StringIO]:
        """
        Return either the main CSV file or the zip file depending on what data channels
        have been requested
        """
        if len(self.zip_file.infolist()) > 0:
            return self.zip_file_in_memory
        else:
            if self.export_scalars:
                return self.main_csv_file_in_memory
            else:
                raise ExportError("Nothing to export")

    def get_filename_stem(self) -> str:
        """
        Create a suitable download filename based on the records ID(s) and, in some
        cases, the channel name.
        For a single record the filename should include the record ID.
        For multiple records the filename should include the first and the last record
        ID.
        If only a single channel is being exported the filename should include that.
        Note that this does not include the file extension.
        """
        first, last = self._get_first_last_record_ids()
        filename = first
        if last is not None:
            filename += "_to_" + last
        if len(self.projection) == 1:
            channel_name = self._get_channel_name(self.projection[0])
            filename += "_" + channel_name
        return filename

    def _get_first_last_record_ids(self) -> Tuple[str, str]:
        """
        Get the first and last record IDs by ordering the list of record IDs and then
        returning the first and last items.
        """
        record_ids_sorted = sorted(self.record_ids)
        first = record_ids_sorted[0]
        if len(record_ids_sorted) == 1:
            last = None
        else:
            last = record_ids_sorted[-1]
        return first, last

    def _add_value_to_csv_line(
        self,
        line: str,
        value: Any,
        verbose: bool = False,
    ) -> str:
        """
        Helper function for writing values to CSV files
        """
        if verbose:
            log.debug("value: %s of type %s", value, type(value))

        if value is None or value == "":
            # leave cell empty in these cases
            return line + ","
        if type(value) == str:
            # put quotes round string values in case they contain a comma
            # which would upset the formatting
            return line + '"' + value + '"' + ","
        else:
            # just put the raw value into the CSV and
            # Excel should do its best to interpret the type
            return line + str(value) + ","

    def _check_zip_file_size(self) -> None:
        """
        Check that the zip file being created in memory is under a maximum size
        specified by a config parameter, otherwise raise an exception
        """
        nbytes = self.zip_file_in_memory.getbuffer().nbytes
        log.info("Zip file size: %d", nbytes)
        if nbytes > ExportHandler.max_filesize_bytes:
            raise ExportError(
                "Too much data requested. Reduce either the number of records or "
                "channels requested, or both.",
            )

    async def _write_to_zip(self, arcname: str, data: str | bytes) -> None:
        """
        As a precaution, lock access to the zip_file to prevent simultaneous access.
        This might not be strictly necessary as zip_file has it's own (synchronous)
        lock, and since writestr is synchronous then the async event loop should not be
        awaiting the outcome of one ongoing writestr while it performs another writestr.
        """
        async with self.zip_lock:
            self.zip_file.writestr(arcname, data)
