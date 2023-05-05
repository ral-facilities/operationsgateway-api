from io import BytesIO
import logging

import boto3

from operationsgateway_api.src.config import Config
from operationsgateway_api.src.exceptions import EchoS3Error


log = logging.getLogger()


class EchoInterface:
    """
    A class containing the functionality needed to contact Echo S3 object storage. In
    OperationsGateway API, this is used to store and retrieve full-size images
    """

    def __init__(self) -> None:
        log.debug("Creating S3 resource to connect to Echo")
        self.resource = boto3.resource(
            "s3",
            endpoint_url=Config.config.images.echo_url,
            aws_access_key_id=Config.config.images.echo_access_key,
            aws_secret_access_key=Config.config.images.echo_secret_key,
        )

        log.debug("Retrieving bucket '%s'", Config.config.images.image_bucket_name)
        self.bucket = self.resource.Bucket(Config.config.images.image_bucket_name)
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
        self.bucket.download_fileobj(Fileobj=image, Key=image_path)
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
        self.bucket.upload_fileobj(image_object, image_path)
        log.debug("Uploaded image successfully to %s", image_path)

    def delete_file_object(self) -> None:
        # TODO - this will be implemented when DELETE /records is implemented
        pass
