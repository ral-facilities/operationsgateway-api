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
    OperationsGateway API, this is used to store and retrieve full-size images.

    In boto3, the same exception class is used for all exceptions, `ClientError`. This
    object has a `response` attribute storing a dictionary containing information of the
    error. The typical format of this dictionary can be found at:
    https://boto3.amazonaws.com/v1/documentation/api/latest/guide/error-handling.html
    """

    def __init__(self) -> None:
        log.debug("Creating S3 resource to connect to Echo")
        try:
            self.resource = boto3.resource(
                "s3",
                endpoint_url=Config.config.images.echo_url,
                aws_access_key_id=Config.config.images.echo_access_key,
                aws_secret_access_key=Config.config.images.echo_secret_key,
            )

            log.debug("Retrieving bucket '%s'", Config.config.images.image_bucket_name)
            self.bucket = self.resource.Bucket(Config.config.images.image_bucket_name)
        except ClientError as exc:
            log.error(
                "%s: %s",
                exc.response["Error"]["Code"],
                exc.response["Error"].get("Message"),
            )
            raise EchoS3Error(
                "Error '%s' caught when creating a boto3 resource and retrieving a"
                " bucket called '%s'",
                exc.response["Error"]["Code"],
                Config.config.images.image_bucket_name,
            ) from exc

        # If a bucket doesn't exist, Bucket() won't raise an exception, so we have to
        # check ourselves. Checking for a creation date means we don't need to make a
        # second call using boto, where a low-level client API call would be needed.
        # See https://stackoverflow.com/a/49817544
        if not self.bucket.creation_date:
            log.error(
                "Bucket cannot be found: %s",
                Config.config.images.image_bucket_name,
            )
            raise EchoS3Error("Bucket for image storage cannot be found")

    def download_file_object(self, image_path: str) -> BytesIO:
        """
        Download an image from S3 using `download_fileobj()`. An image stored in a bytes
        object is returned
        """
        log.info("Download image from Echo: %s", image_path)
        image = BytesIO()
        try:
            self.bucket.download_fileobj(Fileobj=image, Key=image_path)
        except ClientError as exc:
            log.error(
                "%s: %s",
                exc.response["Error"]["Code"],
                exc.response["Error"].get("Message"),
            )
            raise EchoS3Error(
                f"{exc.response['Error']['Code']} when downloading file at"
                f" '{image_path}'",
            ) from exc
        if len(image.getvalue()) == 0:
            log.warning(
                "Image bytes array is empty, image download from S3 might have been"
                " unsuccessful: %s",
                image_path,
            )
        return image

    def upload_file_object(self, image_object: BytesIO, image_path: str) -> None:
        """
        Upload an image from a bytes object
        """
        log.info("Uploading image to %s", image_path)
        image_object.seek(0)
        try:
            self.bucket.upload_fileobj(image_object, image_path)
        except ClientError as exc:
            log.error(
                "%s: %s",
                exc.response["Error"]["Code"],
                exc.response["Error"].get("Message"),
            )
            raise EchoS3Error(
                f"{exc.response['Error']['Code']} when uploading file at"
                f" '{image_path}'",
            ) from exc
        log.debug("Uploaded image successfully to %s", image_path)

    def delete_file_object(self) -> None:
        # TODO - this will be implemented when DELETE /records is implemented
        pass
