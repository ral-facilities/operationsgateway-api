from functools import lru_cache
from io import BytesIO
import logging

import aioboto3
from async_lru import alru_cache
from botocore.exceptions import ClientError
from mypy_boto3_s3.service_resource import Bucket, Object, S3ServiceResource

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
        self.session = aioboto3.Session()
        self._bucket = None  # This will be set by the lifespan of the API on startup

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

    async def put_lifecycle(self) -> None:
        """
        https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3/client/put_bucket_lifecycle_configuration.html
        Puts the lifecycle configuration of the bucket to delete objects after a certain
        number of days.
        """
        expiry_days = Config.config.echo.expiry_days
        bucket_name = Config.config.echo.bucket_name
        if expiry_days is not None:
            log.info("Put expiry lifecycle of %s days for %s", expiry_days, bucket_name)
            rule = {
                "Expiration": {"Days": expiry_days},
                "ID": "expiry",
                "Prefix": "",
                "Status": "Enabled",
            }
            config_dict = {"Rules": [rule]}
            try:
                bucket = await self.get_bucket()
                lifecycle_configuration = await bucket.LifecycleConfiguration()
                await lifecycle_configuration.put(LifecycleConfiguration=config_dict)
            except ClientError:
                log.exception("Failed to put lifecycle for %s", bucket_name)
        else:
            log.info("Expiry lifecycle not configured for %s", bucket_name)

    async def create_bucket(
        self,
        resource: S3ServiceResource,
        cache: bool = False,
    ) -> Bucket:
        """
        Creates an interface to the storage bucket using `resource`. Note that this
        bucket may be closed (no longer usable) when `resource` is closed, namely
        when the context manager closes. Ideally we want to `cache` and re-use the
        bucket to reduce overheads but this should ONLY be done when the app's lifespan
        is going to keep the context open.
        """
        bucket = await resource.Bucket(Config.config.echo.bucket_name)
        if not await bucket.creation_date:
            msg = "Bucket for object storage cannot be found: %s"
            log.error(msg, Config.config.echo.bucket_name)
            raise EchoS3Error("Bucket for object storage cannot be found")

        if cache:
            self._bucket = bucket

        return bucket

    async def get_bucket(self) -> Bucket:
        """
        Utility method for returning the cached `self._bucket`.

        If it does not exist, creates a new resource context manager and returns a new
        Bucket object but does NOT cache. This cannot be cached/re-used as there may
        be multiple concurrent calls and if the context manager closes anything else
        using the bucket will fail. When the API is running we should never reach this,
        but allow it so that EchoInterface can be used directly (e.g. in tests) and as
        defensive code.
        """
        if self._bucket is not None:
            return self._bucket
        else:
            msg = "EchoInterface._bucket unexpectedly None, creating with new resource"
            log.warning(msg)
            async with self.session.resource(
                "s3",
                endpoint_url=Config.config.echo.url,
                aws_access_key_id=Config.config.echo.access_key.get_secret_value(),
                aws_secret_access_key=Config.config.echo.secret_key.get_secret_value(),
            ) as resource:
                return await self.create_bucket(resource)

    async def head_object(self, object_path: str) -> bool:
        """
        https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3/client/head_object.html
        Uses the head operation to check the existence of an object without downloading
        it.
        """
        log.info("Head object in Echo: %s", object_path)
        bucket = await self.get_bucket()
        try:
            await bucket.meta.client.head_object(
                Bucket=Config.config.echo.bucket_name,
                Key=object_path,
            )
            return True
        except ClientError:
            return False

    @alru_cache(maxsize=Config.config.echo.cache_maxsize)
    async def download_file_object(self, object_path: str) -> bytes:
        """
        Download an object from S3 using `download_fileobj()` and return the bytes
        """
        log.info("Download file from Echo: %s", object_path)
        bucket = await self.get_bucket()
        file = BytesIO()
        try:
            await bucket.download_fileobj(Fileobj=file, Key=object_path)
        except ClientError as exc:
            code = exc.response["Error"]["Code"]
            log.exception("%s when downloading file at %s", code, object_path)
            raise EchoS3Error(
                f"{code} when downloading file at '{object_path}'",
                status_code=code,
            ) from exc

        if len(file.getvalue()) == 0:
            log.warning(
                "Bytes array from downloaded object is empty, file download from S3"
                " might have been unsuccessful: %s",
                object_path,
            )

        return file.getvalue()

    async def upload_file_object(self, file_object: BytesIO, object_path: str) -> None:
        """
        Upload a file to S3 (using `upload_fileobj()`) to a given path using a BytesIO
        object
        """
        log.info("Uploading file to %s", object_path)
        bucket = await self.get_bucket()
        file_object.seek(0)
        try:
            await bucket.upload_fileobj(file_object, object_path)
        except ClientError as exc:
            code = exc.response["Error"]["Code"]
            log.exception("%s when uploading file at %s", code, object_path)
            raise EchoS3Error(f"{code} when uploading file at '{object_path}'") from exc

        log.debug("Uploaded file successfully to %s", object_path)

    async def delete_file_object(self, object_path: str) -> None:
        """
        Delete a file from Echo
        """
        log.info("Deleting file from %s", object_path)
        bucket = await self.get_bucket()
        try:
            obj: Object = await bucket.Object(object_path)
            await obj.delete()
        except ClientError as exc:
            code = exc.response["Error"]["Code"]
            log.exception("%s when deleting file at %s", code, object_path)
            raise EchoS3Error(f"{code} when deleting file at '{object_path}'") from exc

    async def delete_directory(self, dir_path: str) -> None:
        """
        Given a path, delete an entire 'directory' from Echo. This is used to delete
        waveforms and images when deleting a record by its ID
        """

        log.info("Deleting directory from %s", dir_path)
        bucket = await self.get_bucket()
        try:
            objects = bucket.objects.filter(Prefix=dir_path)
            await objects.delete()
        except ClientError as exc:
            code = exc.response["Error"]["Code"]
            log.exception("%s when deleting directory %s", code, dir_path)
            raise EchoS3Error(f"{code} when deleting directory '{dir_path}'") from exc


@lru_cache
def get_echo_interface() -> EchoInterface:
    """
    Returns:
        EchoInterface: Cached object for interacting with Echo object storage.
    """
    return EchoInterface()
