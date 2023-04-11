from io import BytesIO

import boto3

from operationsgateway_api.src.config import Config


class EchoInterface:
    """
    TODO
    """

    # TODO - I'll need to create a brand new bucket at the end of development, deleting
    # 'test-bucket' while I'm at it
    # TODO - add docstrings
    # TODO - add type hinting (might be worth looking at boto3-stubs)
    # TODO - add exception handling
    # TODO - add logging
    # TODO - tone down debug logging by S3 libraries, like I did with SOAP stuff

    def __init__(self) -> None:
        self.resource = boto3.resource(
            "s3",
            endpoint_url=Config.config.images.echo_url,
            aws_access_key_id=Config.config.images.echo_access_key,
            aws_secret_access_key=Config.config.images.echo_secret_key,
        )
        self.bucket = self.resource.Bucket(Config.config.images.image_bucket_name)

    def download_file_object(self, image_path):
        image = BytesIO()
        self.bucket.download_fileobj(Fileobj=image, Key=image_path)
        return image

    def upload_file_object(self, image_object: BytesIO, image_path):
        image_object.seek(0)
        self.bucket.upload_fileobj(image_object, image_path)

    def delete_file_object(self):
        # TODO - either implement or add a comment saying this will be implemented when
        # full functionality of deleting records is added
        pass

    def list_objects(self, prefix=""):
        objects = self.bucket.objects.filter(Prefix=prefix)
        for o in objects:
            print(f"Key: {o.key}, Last Modified: {o.last_modified}, Size: {o.size}")
