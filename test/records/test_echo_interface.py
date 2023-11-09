from io import BytesIO
from unittest.mock import patch

from operationsgateway_api.src.records.echo_interface import EchoInterface


class TestEchoInterface:
    config_echo_url = "https://mytesturl.com"
    config_echo_access_key = "TestAccessKey"
    config_echo_secret_key = "TestSecretKey"
    config_image_bucket_name = "MyTestBucket"
    test_image_path = "test/image/path.png"

    @patch(
        "operationsgateway_api.src.config.Config.config.images.echo_url",
        config_echo_url,
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.images.echo_access_key",
        config_echo_access_key,
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.images.echo_secret_key",
        config_echo_secret_key,
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.images.image_bucket_name",
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
        "operationsgateway_api.src.config.Config.config.images.echo_url",
        config_echo_url,
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.images.echo_access_key",
        config_echo_access_key,
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.images.echo_secret_key",
        config_echo_secret_key,
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.images.image_bucket_name",
        config_image_bucket_name,
    )
    @patch("boto3.resource")
    def test_download_file_object(self, _):
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
        "operationsgateway_api.src.config.Config.config.images.echo_url",
        config_echo_url,
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.images.echo_access_key",
        config_echo_access_key,
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.images.echo_secret_key",
        config_echo_secret_key,
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.images.image_bucket_name",
        config_image_bucket_name,
    )
    @patch("boto3.resource")
    def test_upload_file_object(self, _):
        test_echo = EchoInterface()

        test_echo.upload_file_object(BytesIO(), self.test_image_path)
        assert test_echo.bucket.upload_fileobj.call_count == 1
