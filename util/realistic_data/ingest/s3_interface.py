from io import BytesIO
from time import time

import boto3
from util.realistic_data.ingest.config import Config


class S3Interface:
    def __init__(self) -> None:
        self.resource = boto3.resource(
            "s3",
            endpoint_url=Config.config.echo.endpoint_url,
            aws_access_key_id=Config.config.echo.access_key,
            aws_secret_access_key=Config.config.echo.secret_key,
        )
        self.client = boto3.client(
            "s3",
            endpoint_url=Config.config.echo.endpoint_url,
            aws_access_key_id=Config.config.echo.access_key,
            aws_secret_access_key=Config.config.echo.secret_key,
        )
        self.simulated_data_bucket = self.resource.Bucket(
            Config.config.echo.simulated_data_bucket,
        )
        self.bucket = self.resource.Bucket(Config.config.echo.storage_bucket)

    def download_manifest_file(self) -> BytesIO:
        channel_manifest = BytesIO()
        self.simulated_data_bucket.download_fileobj(
            Fileobj=channel_manifest,
            Key="resources/channel_manifest.json",
        )
        channel_manifest.seek(0)
        print("Downloaded channel manifest file from S3")
        return channel_manifest

    def download_experiments(self) -> BytesIO:
        experiments_import = BytesIO()
        self.simulated_data_bucket.download_fileobj(
            Fileobj=experiments_import,
            Key="resources/experiments_for_mongoimport.json",
        )
        experiments_import.seek(0)
        print("Downloaded experiments (in format for mongoimport) from S3")
        return experiments_import

    def paginate_hdf_data(self):
        paginator = self.client.get_paginator("list_objects_v2")
        return paginator.paginate(
            Bucket=Config.config.echo.simulated_data_bucket,
            Prefix="data/",
            PaginationConfig={"PageSize": Config.config.echo.page_size},
        )

    def download_hdf_file(self, object_key: str):
        download_start_time = time()
        hdf_file = BytesIO()
        self.simulated_data_bucket.download_fileobj(
            Fileobj=hdf_file,
            Key=object_key,
        )
        hdf_file.seek(0)
        download_end_time = time()
        download_duration = download_end_time - download_start_time
        print(f"Downloaded: {object_key}, Duration: {download_duration:0.2f} seconds")

        return {object_key: hdf_file}

    def delete_all(self):
        self.bucket.objects.all().delete()
        print("Removed all objects from bucket")
