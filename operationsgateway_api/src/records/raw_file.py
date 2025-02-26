from io import BytesIO
import logging

from botocore.exceptions import ClientError

from operationsgateway_api.src.exceptions import (
    EchoS3Error,
    RawFileError,
    RawFileNotFoundError,
)
from operationsgateway_api.src.models import RawFileModel
from operationsgateway_api.src.mongo.interface import MongoDBInterface
from operationsgateway_api.src.records.echo_interface import EchoInterface


log = logging.getLogger()


class RawFile:
    echo_prefix = "raw_files"

    def __init__(self, raw_file: RawFileModel) -> None:
        self.raw_file = raw_file

    def insert_raw_file(self) -> str | None:
        """
        Upload the bytes of this raw file to storage. Returns the channel name if the
        upload fails.
        """
        log.info("Storing raw file: %s", self.raw_file.path)
        echo = EchoInterface()
        try:
            echo.upload_file_object(
                BytesIO(self.raw_file.data),
                RawFile.get_full_path(self.raw_file.path),
            )
            return  # Successful upload
        except EchoS3Error:
            # Extract the channel name and propagate it
            channel_name = self.get_channel_name_from_path()
            log.exception(
                "Failed to upload raw file for channel '%s'",
                channel_name,
            )
            return channel_name

    @staticmethod
    async def get_raw_file(record_id: str, channel_name: str) -> BytesIO:
        """
        Retrieve the bytes of a raw file from storage and return as BytesIO.
        """

        log.info("Retrieving raw file and returning BytesIO object")
        echo = EchoInterface()

        try:
            relative_path = RawFile.get_relative_path(record_id, channel_name)
            return echo.download_file_object(RawFile.get_full_path(relative_path))
        except (ClientError, EchoS3Error) as exc:
            # Record.count_records() could not be used because that would cause a
            # circular import
            record_count = await MongoDBInterface.count_documents(
                "records",
                {
                    "_id": record_id,
                    f"channels.{channel_name}": {"$exists": True},
                },
            )

            if record_count == 1:
                msg = "Raw file could not be found on object storage"
                log_msg = msg + ". Record ID: %s, channel name: %s"
                log.error(log_msg, record_id, channel_name)
                raise RawFileError(msg) from exc
            elif record_count == 0:
                msg_record = "Raw file not available due to incorrect record ID"
                msg_channel = " or channel name"
                log_msg = msg_record + " (%s)" + msg_channel + " (%s)"
                log.error(log_msg, record_id, channel_name)
                raise RawFileNotFoundError(msg_record + msg_channel) from exc
            else:
                msg = "Unexpected error finding raw file on object storage"
                log_msg = (
                    "Unexpected number of records (%d) found when verifying whether the"
                    " raw file should be available on object storage"
                )
                log.error(log_msg, record_count)
                raise RawFileError(msg) from exc

    def get_channel_name_from_path(self) -> str:
        """
        Get the channel name from the storage path.
        """
        return self.raw_file.path.split("/")[-1]

    @staticmethod
    def get_relative_path(record_id: str, channel_name: str) -> str:
        """
        Returns a relative path given a record id and channel name. The path is relative
        to the base directory.
        """
        return f"{record_id}/{channel_name}"

    @staticmethod
    def get_full_path(relative_path: str) -> str:
        """
        Returns the full path by adding the storage base directory to the start of the
        path. The full path does not include the bucket name.
        """
        return f"{RawFile.echo_prefix}/{relative_path}"
