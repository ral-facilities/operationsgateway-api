from ast import literal_eval
import io
import logging
from typing import Dict, List, Tuple, Union
import zipfile

from operationsgateway_api.src.config import Config
from operationsgateway_api.src.exceptions import ExportError
from operationsgateway_api.src.records.image import Image
from operationsgateway_api.src.records.waveform import Waveform


log = logging.getLogger()


class ExportHandler:
    max_filesize_bytes = Config.config.export.max_filesize_bytes

    def __init__(
        self,
        records_data: List[dict],
        channel_manifest_dict: dict,
        projection: List[str],
        lower_level: int,
        upper_level: int,
        colourmap_name: str,
        export_scalars: bool,
        export_images: bool,
        export_waveform_csvs: bool,
        export_waveform_images: bool,
    ) -> None:
        """
        Store all of the information that needs to be processed during the export
        """
        self.records_data = records_data
        self.channel_manifest_dict = channel_manifest_dict
        self.projection = projection
        self.lower_level = lower_level
        self.upper_level = upper_level
        self.colourmap_name = colourmap_name
        self.export_scalars = export_scalars
        self.export_images = export_images
        self.export_waveform_csvs = export_waveform_csvs
        self.export_waveform_images = export_waveform_images

        self.record_ids = []
        self.errors_file_in_memory = io.StringIO()
        self.main_csv_file_in_memory = io.StringIO()
        self.zip_file_in_memory = io.BytesIO()
        self.zip_file = zipfile.ZipFile(
            self.zip_file_in_memory,
            "a",
            zipfile.ZIP_DEFLATED,
            False,
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
        self._create_main_csv_headers()
        for record_data in self.records_data:
            log.info("record_data: %s", record_data)
            record_id = record_data["_id"]
            self.record_ids.append(record_id)
            log.info("record_id: %s", record_id)

            line = ""
            for proj in self.projection:
                projection_parts = proj.split(".")
                channel_name = projection_parts[1]
                log.info("channel_name: %s", channel_name)
                if projection_parts[0] == "metadata":
                    # process one of the main "metadata" channels
                    value = ExportHandler.get_value_from_dict(record_data, proj)
                    log.info("value: %s of type %s", value, type(value))
                    line = ExportHandler.add_value_to_csv_line(line, value)
                elif projection_parts[0] == "channels":
                    # process one of the data channels
                    line = await self._process_data_channel(
                        record_data,
                        record_id,
                        channel_name,
                        line,
                        proj,
                    )
                else:
                    log.warning(
                        "Unrecognised first projection part: %s",
                        projection_parts[0],
                    )

            # don't put empty lines in the CSV file
            if line != "":
                self.main_csv_file_in_memory.write(line + "\n")

        self._add_main_csv_file_to_zip()
        self._add_messages_file_to_zip()

        # end of adding files to the zip file
        # close the file to finish writing the directory entry etc.
        self.zip_file.close()

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
            projection_parts = proj.split(".")
            channel_name = projection_parts[1]
            if projection_parts[0] == "channels":
                # image and waveform data will be exported to separate files so will not
                # have values put in the main csv file
                if (
                    self.channel_manifest_dict["channels"][channel_name]["type"]
                ) not in ["image", "waveform"]:
                    line = ExportHandler.add_value_to_csv_line(line, channel_name)
            else:
                # this must be a "metadata" channel
                line = ExportHandler.add_value_to_csv_line(line, channel_name)
        # don't put empty lines in the CSV file
        if line != "":
            self.main_csv_file_in_memory.write(line + "\n")

    async def _process_data_channel(
        self,
        record_data: Dict,
        record_id: str,
        channel_name: str,
        line: str,
        projection: str,
    ) -> str:
        """
        Process data channels (those whose "projection" starts with "channels." as
        opposed to metadata channels whose projection starts with "metadata.") by
        adding image and waveform files to a zip file and scalar data to a line of text
        that will be added to the main CSV file.
        """
        # process an image channel
        if self.channel_manifest_dict["channels"][channel_name]["type"] == "image":
            log.info("Channel %s is an image", channel_name)
            if self.export_images:
                await self._add_image_to_zip(record_data, record_id, channel_name)
        # process a waveform channel
        elif self.channel_manifest_dict["channels"][channel_name]["type"] == "waveform":
            log.info("Channel %s is a waveform", channel_name)
            try:
                x_units = record_data["channels"][channel_name]["metadata"]["x_units"]
            except KeyError:
                x_units = ""
            try:
                y_units = record_data["channels"][channel_name]["metadata"]["y_units"]
            except KeyError:
                y_units = ""
            await self._add_waveform_to_zip(
                record_data,
                record_id,
                channel_name,
                x_units,
                y_units,
            )
        # process a scalar channel
        else:
            log.info("Channel %s is a scalar", channel_name)
            value = ExportHandler.get_value_from_dict(record_data, projection)
            log.info("value: %s of type %s", value, type(value))
            line = ExportHandler.add_value_to_csv_line(line, value)
        return line

    async def _add_image_to_zip(
        self,
        record_data: Dict,
        record_id: str,
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
        try:
            # first check that there should be an image to process
            _ = record_data["channels"][channel_name]
        except KeyError:
            # there is no entry for this channel in the record
            # so there is no image to process
            return

        log.info("Getting image to add to zip: %s %s", record_id, channel_name)
        # if none of the false colour parameters are set then the original
        # image is required
        original_image = (
            self.lower_level == 0
            and self.upper_level == 255
            and self.colourmap_name is None
        )
        try:
            if record_id == "20220407142816":
                raise ExportError("Couldn't find this file!")
            image_bytes = await Image.get_image(
                record_id,
                channel_name,
                original_image,
                self.lower_level,
                self.upper_level,
                self.colourmap_name,
            )
            self.zip_file.writestr(
                f"{record_id}_{channel_name}.png",
                image_bytes.getvalue(),
            )
            ExportHandler.check_zip_file_size(self.zip_file_in_memory)
        except Exception:
            self.errors_file_in_memory.write(
                f"Could not find image for {record_id} {channel_name}\n",
            )

    async def _add_waveform_to_zip(
        self,
        record_data: Dict,
        record_id: str,
        channel_name: str,
        x_units: str,
        y_units: str,
    ) -> None:
        """
        Get the arrays of x and y values for a waveform and then either write them to a
        CSV file or create a rendered image of the waveform (or both) and add the
        created file(s) to the zip file being created ready for download.
        """
        try:
            # first check that there should be a waveform to process
            _ = record_data["channels"][channel_name]
        except KeyError:
            # there is no entry for this channel in the record
            # so there is no waveform to process
            return

        if self.export_waveform_csvs or self.export_waveform_images:
            log.info(
                "Getting waveform to add to zip: %s %s",
                record_id,
                channel_name,
            )
            try:
                waveform_model = await Waveform.get_waveform(
                    f"{record_id}_{channel_name}",
                )
            except Exception:
                self.errors_file_in_memory.write(
                    f"Could not find waveform for {record_id} {channel_name}\n",
                )
                # no point trying to process the waveform so return at this point
                return

            if self.export_waveform_csvs:
                # TODO: this is taking the x and y values from the Waveform that
                # are currently strings that look like arrays and converting them
                # to actual arrays
                # There is a currently unmerged PR which will change these strings
                # to arrays of floats, at which point the string to array
                # conversion being done here can be removed
                x_array = literal_eval(waveform_model.x)
                y_array = literal_eval(waveform_model.y)
                num_points = len(x_array)
                waveform_csv_in_memory = io.StringIO()
                for point_num in range(num_points):
                    waveform_csv_in_memory.write(
                        str(x_array[point_num]) + "," + str(y_array[point_num]) + "\n",
                    )
                self.zip_file.writestr(
                    f"{record_id}_{channel_name}.csv",
                    waveform_csv_in_memory.getvalue(),
                )
                ExportHandler.check_zip_file_size(self.zip_file_in_memory)

            if self.export_waveform_images:
                # if rendered trace images have been requested then add those
                waveform = Waveform(waveform_model)
                waveform_png_bytes = waveform.get_fullsize_png(x_units, y_units)
                self.zip_file.writestr(
                    f"{record_id}_{channel_name}.png",
                    waveform_png_bytes,
                )
                ExportHandler.check_zip_file_size(self.zip_file_in_memory)

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
                ExportHandler.check_zip_file_size(self.zip_file_in_memory)

    def _add_messages_file_to_zip(self):
        """
        Add a file listing any errors that might be useful to the user to the zip such
        as any files or waveforms that were not found.
        """
        if len(self.errors_file_in_memory.getvalue()) > 0:
            self.zip_file.writestr(
                "EXPORT_ERRORS.txt",
                self.errors_file_in_memory.getvalue(),
            )

    def get_export_file_bytes(self) -> Union[io.BytesIO, io.StringIO]:
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
        first, last = ExportHandler.get_first_last_record_ids(self.record_ids)
        filename = first
        if last is not None:
            filename += "_to_" + last
        if len(self.projection) == 1:
            channel_name = self.projection[0].split(".")[1]
            filename += "_" + channel_name
        return filename

    @staticmethod
    def get_first_last_record_ids(record_ids: List) -> Tuple[str, str]:
        """
        Get the first and last record IDs by ordering the list of record IDs and then
        returning the first and last items.
        """
        record_ids_sorted = sorted(record_ids)
        first = record_ids_sorted[0]
        if len(record_ids_sorted) == 1:
            last = None
        else:
            last = record_ids_sorted[-1]
        return first, last

    @staticmethod
    def add_value_to_csv_line(line, value) -> str:
        """
        Helper function for writing values to CSV files
        """
        if type(value) == str:
            # put quotes round string values in case they contain a comma
            # which would upset the formatting
            return line + '"' + value + '"' + ","
        else:
            # just put the raw value into the CSV and
            # Excel should do its best to interpret the type
            return line + str(value) + ","

    @staticmethod
    def get_value_from_dict(record_dict, projection) -> Union[str, int, float, Dict]:
        """
        Recursive function to extract a value from a record dictionary by traversing
        down the dictionary following a path specified by the projection to reach a
        scalar value which is then returned.
        The recursion handles values that are found at different depths in the record
        dictionary such as metadata.shotnum and channels.N_COMP_FF_E.data.
        """
        # get the projection part up to the first dot
        projection_array = projection.split(".")
        next_projection_part = projection_array[0]
        try:
            # get either the entry in the dictionary
            # or a value if we have reached the value we need
            dict_or_value = record_dict.get(next_projection_part)
        except AttributeError:
            # there is no value for this item in this record - this is probably OK
            # return empty string so that alignment is maintained in the CSV file
            return ""
        if len(projection_array) == 1:
            # we should have reached an item value in the most nested dictionary
            # so return it
            return dict_or_value
        else:
            # we still have a dictionary which needs further processing
            # to get down to lower levels where the value will be
            new_projection = projection.split(".", 1)[1]
            return ExportHandler.get_value_from_dict(dict_or_value, new_projection)

    @staticmethod
    def check_zip_file_size(zip_file_in_memory: io.BytesIO) -> None:
        """
        Check that the zip file being created in memory is under a maximum size
        specified by a config parameter, otherwise raise an exception
        """
        nbytes = zip_file_in_memory.getbuffer().nbytes
        log.info("Zip file size: %d", nbytes)
        if nbytes > ExportHandler.max_filesize_bytes:
            raise ExportError(
                "Too much data requested. Reduce either the number of records or "
                "channels requested, or both.",
            )
