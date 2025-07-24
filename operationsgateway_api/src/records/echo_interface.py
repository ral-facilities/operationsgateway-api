from functools import lru_cache
from io import BytesIO
import logging

import boto3
from botocore.exceptions import ClientError

from operationsgateway_api.src.config import Config
from operationsgateway_api.src.exceptions import EchoS3Error


log = logging.getLogger()


class EchoInterface:
    """
    A class containing the functionality needed to contact Echo S3 object storage. In
    OperationsGateway API, this is used to store and retrieve full-size images and
    waveform data.

    In boto3, the same exception class is used for all exceptions, `ClientError`. This
    object has a `response` attribute storing a dictionary containing information of the
    error. The typical format of this dictionary can be found at:
    https://boto3.amazonaws.com/v1/documentation/api/latest/guide/error-handling.html
    """

    def __init__(self) -> None:
        log.debug("Creating S3 resource to connect to Echo")
        try:
            self.client = boto3.client(
                "s3",
                endpoint_url=Config.config.echo.url,
                aws_access_key_id=Config.config.echo.access_key.get_secret_value(),
                aws_secret_access_key=Config.config.echo.secret_key.get_secret_value(),
            )
            self.resource = boto3.resource(
                "s3",
                endpoint_url=Config.config.echo.url,
                aws_access_key_id=Config.config.echo.access_key.get_secret_value(),
                aws_secret_access_key=Config.config.echo.secret_key.get_secret_value(),
            )

            log.debug("Retrieving bucket '%s'", Config.config.echo.bucket_name)
            self.bucket = self.resource.Bucket(Config.config.echo.bucket_name)
        except ClientError as exc:
            log.error(
                "%s: %s. This error happened with bucket '%s'",
                exc.response["Error"]["Code"],
                exc.response["Error"].get("Message"),
                Config.config.echo.bucket_name,
            )
            raise EchoS3Error(
                "Error retrieving object storage bucket:"
                f" {exc.response['Error']['Code']}",
            ) from exc

        # If a bucket doesn't exist, Bucket() won't raise an exception, so we have to
        # check ourselves. Checking for a creation date means we don't need to make a
        # second call using boto, where a low-level client API call would be needed.
        # See https://stackoverflow.com/a/49817544
        if not self.bucket.creation_date:
            log.error(
                "Bucket cannot be found: %s",
                Config.config.echo.bucket_name,
            )
            raise EchoS3Error("Bucket for object storage cannot be found")

    @staticmethod
    def format_record_id(record_id: str, use_subdirectories: bool = True) -> str:
        """
        Historically, objects had their record_id (YYYYMMDDHHMMSS) as a directory. This
        can lead to large (~100,000) numbers of directories in the same bucket which
        take too long to list when debugging.

        By splitting the directories into the format YYYY/MM/DD/HHMMSS, the hope is to
        improve findability. However since migrating large amounts of data can be
        costly, it may be practical to support both the new and old formats when
        querying.
        """
        if use_subdirectories and len(record_id) > 8:
            return f"{record_id[:4]}/{record_id[4:6]}/{record_id[6:8]}/{record_id[8:]}"
        else:
            return record_id

    def head_object(self, object_path: str) -> bool:
        """
        https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3/client/head_object.html
        Uses the head operation to check the existence of an object without downloading
        it.
        """
        log.info("Head object in Echo: %s", object_path)
        try:
            self.client.head_object(
                Bucket=Config.config.echo.bucket_name,
                Key=object_path,
            )
            return True
        except ClientError:
            return False

    def download_file_object(self, object_path: str) -> BytesIO:
        """
        Download an object from S3 using `download_fileobj()` and return a BytesIO
        object
        """
        log.info("Download file from Echo: %s", object_path)
        file = BytesIO()
        try:
            self.bucket.download_fileobj(Fileobj=file, Key=object_path)
        except ClientError as exc:
            log.error(
                "%s: %s",
                exc.response["Error"]["Code"],
                exc.response["Error"].get("Message"),
            )
            raise EchoS3Error(
                f"{exc.response['Error']['Code']} when downloading file at"
                f" '{object_path}'",
            ) from exc
        if len(file.getvalue()) == 0:
            log.warning(
                "Bytes array from downloaded object is empty, file download from S3"
                " might have been unsuccessful: %s",
                object_path,
            )
        return file

    def upload_file_object(self, file_object: BytesIO, object_path: str) -> None:
        """
        Upload a file to S3 (using `upload_fileobj()`) to a given path using a BytesIO
        object
        """
        log.info("Uploading file to %s", object_path)
        file_object.seek(0)
        try:
            self.bucket.upload_fileobj(file_object, object_path)
        except ClientError as exc:
            log.error(
                "%s: %s",
                exc.response["Error"]["Code"],
                exc.response["Error"].get("Message"),
            )
            raise EchoS3Error(
                f"{exc.response['Error']['Code']} when uploading file at"
                f" '{object_path}'",
            ) from exc
        log.debug("Uploaded file successfully to %s", object_path)

    def delete_file_object(self, object_path: str) -> None:
        """
        Delete a file from Echo
        """
        log.info("Deleting file from %s", object_path)
        try:
            self.bucket.Object(object_path).delete()
        except ClientError as exc:
            log.error(
                "%s: %s",
                exc.response["Error"]["Code"],
                exc.response["Error"].get("Message"),
            )
            raise EchoS3Error(
                f"{exc.response['Error']['Code']} when deleting file at"
                f" '{object_path}'",
            ) from exc

        obj = self.bucket.Object(object_path)
        try:
            obj.load()
        except ClientError as exc:
            if exc.response["Error"]["Code"] != "404":
                log.error(
                    "The object with key %s still exists. Deletion might not "
                    "have been successful.",
                    object_path,
                )
                raise EchoS3Error(
                    f"Deletion of {object_path} was unsuccessful",
                ) from exc

    def delete_directory(self, dir_path: str) -> None:
        """
        Given a path, delete an entire 'directory' from Echo. This is used to delete
        waveforms and images when deleting a record by its ID
        """

        log.info("Deleting directory from %s", dir_path)

        try:
            self.bucket.objects.filter(Prefix=dir_path).delete()
        except ClientError as exc:
            log.error(
                "%s: %s",
                exc.response["Error"]["Code"],
                exc.response["Error"].get("Message"),
            )
            raise EchoS3Error(
                f"{exc.response['Error']['Code']} when deleting file at"
                f" '{dir_path}'",
            ) from exc


@lru_cache
def get_echo_interface() -> EchoInterface:
    """
    Returns:
        EchoInterface: Cached object for interacting with Echo object storage.
    """
    return EchoInterface()
