from io import BytesIO
from unittest.mock import patch

from botocore.exceptions import ClientError
import pytest

from operationsgateway_api.src.exceptions import EchoS3Error
from operationsgateway_api.src.records.echo_interface import EchoInterface


class TestEchoInterface:
    config_echo_url = "https://mytesturl.com"
    config_echo_access_key = "TestAccessKey"
    config_echo_secret_key = "TestSecretKey"
    config_image_bucket_name = "MyTestBucket"
    test_image_path = "test/image/path.png"

    @patch(
        "operationsgateway_api.src.config.Config.config.echo.url",
        config_echo_url,
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.echo.access_key",
        config_echo_access_key,
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.echo.secret_key",
        config_echo_secret_key,
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.echo.bucket_name",
        config_image_bucket_name,
    )
    @patch("boto3.resource")
    def test_valid_init(self, mock_resource):
        test_echo = EchoInterface()

        assert mock_resource.call_count == 1
        expected_resource_args = ("s3",)
        expected_resource_kwargs = {
            "endpoint_url": self.config_echo_url,
            "aws_access_key_id": self.config_echo_access_key,
            "aws_secret_access_key": self.config_echo_secret_key,
        }
        assert mock_resource.call_args.args == expected_resource_args
        assert mock_resource.call_args.kwargs == expected_resource_kwargs

        assert test_echo.resource.Bucket.call_count == 1
        expected_bucket_args = (self.config_image_bucket_name,)
        assert test_echo.resource.Bucket.call_args.args == expected_bucket_args

    @patch(
        "operationsgateway_api.src.config.Config.config.echo.url",
        config_echo_url,
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.echo.access_key",
        config_echo_access_key,
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.echo.secret_key",
        config_echo_secret_key,
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.echo.bucket_name",
        config_image_bucket_name,
    )
    @patch("boto3.resource")
    def test_invalid_init(self, mock_resource):
        with patch("boto3.resource") as mock_resource:
            mock_resource.side_effect = ClientError(
                {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
                "resource",
            )

            with pytest.raises(
                EchoS3Error,
                match="Error retrieving object storage bucket:",
            ):
                EchoInterface()

        with patch("boto3.resource") as mock_resource:
            mock_bucket_instance = mock_resource.return_value.Bucket.return_value

            mock_bucket_instance.creation_date = None

            with pytest.raises(
                EchoS3Error,
                match="Bucket for object storage cannot be found",
            ):
                EchoInterface()

    @patch(
        "operationsgateway_api.src.config.Config.config.echo.url",
        config_echo_url,
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.echo.access_key",
        config_echo_access_key,
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.echo.secret_key",
        config_echo_secret_key,
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.echo.bucket_name",
        config_image_bucket_name,
    )
    @patch("boto3.resource")
    def test_valid_download_file_object(self, _):
        test_echo = EchoInterface()

        test_image = test_echo.download_file_object(self.test_image_path)

        assert test_image.getvalue() == BytesIO().getvalue()

        assert test_echo.bucket.download_fileobj.call_count == 1
        # Can't assert on both at the same time as per test_valid_init() as memory
        # addresses of ByteIO object will be different
        assert (
            type(test_echo.bucket.download_fileobj.call_args.kwargs["Fileobj"])
            == BytesIO
        )
        assert (
            test_echo.bucket.download_fileobj.call_args.kwargs["Key"]
            == self.test_image_path
        )

    @patch(
        "operationsgateway_api.src.config.Config.config.echo.url",
        config_echo_url,
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.echo.access_key",
        config_echo_access_key,
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.echo.secret_key",
        config_echo_secret_key,
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.echo.bucket_name",
        config_image_bucket_name,
    )
    @patch("boto3.resource")
    def test_invalid_download_file_object(self, _):
        with patch("boto3.resource") as mock_resource:
            mock_bucket = mock_resource.return_value.Bucket.return_value

            mock_bucket.download_fileobj.side_effect = ClientError(
                {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
                "download_fileobj",
            )

            test_echo = EchoInterface()

            with pytest.raises(EchoS3Error, match="when downloading file at"):
                test_echo.download_file_object(self.test_image_path)

    @patch(
        "operationsgateway_api.src.config.Config.config.echo.url",
        config_echo_url,
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.echo.access_key",
        config_echo_access_key,
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.echo.secret_key",
        config_echo_secret_key,
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.echo.bucket_name",
        config_image_bucket_name,
    )
    @patch("boto3.resource")
    def test_valid_upload_file_object(self, _):
        test_echo = EchoInterface()

        test_echo.upload_file_object(BytesIO(), self.test_image_path)
        assert test_echo.bucket.upload_fileobj.call_count == 1

    @patch(
        "operationsgateway_api.src.config.Config.config.echo.url",
        config_echo_url,
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.echo.access_key",
        config_echo_access_key,
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.echo.secret_key",
        config_echo_secret_key,
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.echo.bucket_name",
        config_image_bucket_name,
    )
    @patch("boto3.resource")
    def test_invalid_upload_file_object(self, _):
        with patch("boto3.resource") as mock_resource:
            mock_bucket = mock_resource.return_value.Bucket.return_value

            mock_bucket.upload_fileobj.side_effect = ClientError(
                {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
                "upload_fileobj",
            )

            test_echo = EchoInterface()

            with pytest.raises(EchoS3Error, match="when uploading file at"):
                test_echo.upload_file_object(BytesIO(), self.test_image_path)

    @patch(
        "operationsgateway_api.src.config.Config.config.echo.url",
        config_echo_url,
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.echo.access_key",
        config_echo_access_key,
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.echo.secret_key",
        config_echo_secret_key,
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.echo.bucket_name",
        config_image_bucket_name,
    )
    @patch("boto3.resource")
    def test_valid_delete_file_object(self, _):
        test_echo = EchoInterface()

        test_echo.delete_file_object(self.test_image_path)
        assert test_echo.bucket.Object.return_value.delete.call_count == 1

    @patch(
        "operationsgateway_api.src.config.Config.config.echo.url",
        config_echo_url,
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.echo.access_key",
        config_echo_access_key,
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.echo.secret_key",
        config_echo_secret_key,
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.echo.bucket_name",
        config_image_bucket_name,
    )
    @patch("boto3.resource")
    def test_invalid_delete_file_object(self, _):
        with patch("boto3.resource") as mock_resource:
            mock_bucket = mock_resource.return_value.Bucket.return_value

            mock_bucket.Object.return_value.delete.side_effect = ClientError(
                {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
                "delete",
            )

            test_echo = EchoInterface()

            with pytest.raises(EchoS3Error, match="when deleting file at"):
                test_echo.delete_file_object(self.test_image_path)

        with patch("boto3.resource") as mock_resource:
            mock_bucket = mock_resource.return_value.Bucket.return_value

            mock_bucket.Object.return_value.load.side_effect = ClientError(
                {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
                "delete",
            )

            test_echo = EchoInterface()
            with pytest.raises(EchoS3Error):
                test_echo.delete_file_object(self.test_image_path)
