# from io import BytesIO
# from unittest.mock import patch

# from botocore.exceptions import ClientError
# from pydantic import SecretStr
# import pytest

# from operationsgateway_api.src.exceptions import EchoS3Error
# from operationsgateway_api.src.records.echo_interface import EchoInterface


# class TestEchoInterface:
#     config_echo_url = "https://mytesturl.com"
#     config_echo_access_key = SecretStr("TestAccessKey")
#     config_echo_secret_key = SecretStr("TestSecretKey")
#     config_image_bucket_name = "MyTestBucket"
#     test_image_path = "test/image/path.png"

#     @pytest.mark.asyncio
#     @patch(
#         "operationsgateway_api.src.config.Config.config.echo.url",
#         config_echo_url,
#     )
#     @patch(
#         "operationsgateway_api.src.config.Config.config.echo.access_key",
#         config_echo_access_key,
#     )
#     @patch(
#         "operationsgateway_api.src.config.Config.config.echo.secret_key",
#         config_echo_secret_key,
#     )
#     @patch(
#         "operationsgateway_api.src.config.Config.config.echo.bucket_name",
#         config_image_bucket_name,
#     )
#     @patch("boto3.resource")
#     async def test_valid_download_file_object(self, _):
#         test_echo = EchoInterface()

#         test_image = await test_echo.download_file_object(self.test_image_path)

#         assert test_image.getvalue() == BytesIO().getvalue()

#         assert test_echo.bucket.download_fileobj.call_count == 1
#         # Can't assert on both at the same time as per test_valid_init() as memory
#         # addresses of ByteIO object will be different
#         assert (
#             type(test_echo.bucket.download_fileobj.call_args.kwargs["Fileobj"])
#             == BytesIO
#         )
#         assert (
#             test_echo.bucket.download_fileobj.call_args.kwargs["Key"]
#             == self.test_image_path
#         )

#     @pytest.mark.asyncio
#     @patch(
#         "operationsgateway_api.src.config.Config.config.echo.url",
#         config_echo_url,
#     )
#     @patch(
#         "operationsgateway_api.src.config.Config.config.echo.access_key",
#         config_echo_access_key,
#     )
#     @patch(
#         "operationsgateway_api.src.config.Config.config.echo.secret_key",
#         config_echo_secret_key,
#     )
#     @patch(
#         "operationsgateway_api.src.config.Config.config.echo.bucket_name",
#         config_image_bucket_name,
#     )
#     @patch("boto3.resource")
#     async def test_invalid_download_file_object(self, _):
#         with patch("boto3.resource") as mock_resource:
#             mock_bucket = mock_resource.return_value.Bucket.return_value

#             mock_bucket.download_fileobj.side_effect = ClientError(
#                 {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
#                 "download_fileobj",
#             )

#             test_echo = EchoInterface()

#             with pytest.raises(EchoS3Error, match="when downloading file at"):
#                 await test_echo.download_file_object(self.test_image_path)

#     @pytest.mark.asyncio
#     @patch(
#         "operationsgateway_api.src.config.Config.config.echo.url",
#         config_echo_url,
#     )
#     @patch(
#         "operationsgateway_api.src.config.Config.config.echo.access_key",
#         config_echo_access_key,
#     )
#     @patch(
#         "operationsgateway_api.src.config.Config.config.echo.secret_key",
#         config_echo_secret_key,
#     )
#     @patch(
#         "operationsgateway_api.src.config.Config.config.echo.bucket_name",
#         config_image_bucket_name,
#     )
#     @patch("boto3.resource")
#     async def test_valid_upload_file_object(self, _):
#         test_echo = EchoInterface()

#         await test_echo.upload_file_object(BytesIO(), self.test_image_path)
#         assert test_echo.bucket.upload_fileobj.call_count == 1

#     @pytest.mark.asyncio
#     @patch(
#         "operationsgateway_api.src.config.Config.config.echo.url",
#         config_echo_url,
#     )
#     @patch(
#         "operationsgateway_api.src.config.Config.config.echo.access_key",
#         config_echo_access_key,
#     )
#     @patch(
#         "operationsgateway_api.src.config.Config.config.echo.secret_key",
#         config_echo_secret_key,
#     )
#     @patch(
#         "operationsgateway_api.src.config.Config.config.echo.bucket_name",
#         config_image_bucket_name,
#     )
#     @patch("boto3.resource")
#     async def test_invalid_upload_file_object(self, _):
#         with patch("boto3.resource") as mock_resource:
#             mock_bucket = mock_resource.return_value.Bucket.return_value

#             mock_bucket.upload_fileobj.side_effect = ClientError(
#                 {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
#                 "upload_fileobj",
#             )

#             test_echo = EchoInterface()

#             with pytest.raises(EchoS3Error, match="when uploading file at"):
#                 await test_echo.upload_file_object(BytesIO(), self.test_image_path)

#     @pytest.mark.asyncio
#     @patch(
#         "operationsgateway_api.src.config.Config.config.echo.url",
#         config_echo_url,
#     )
#     @patch(
#         "operationsgateway_api.src.config.Config.config.echo.access_key",
#         config_echo_access_key,
#     )
#     @patch(
#         "operationsgateway_api.src.config.Config.config.echo.secret_key",
#         config_echo_secret_key,
#     )
#     @patch(
#         "operationsgateway_api.src.config.Config.config.echo.bucket_name",
#         config_image_bucket_name,
#     )
#     @patch("boto3.resource")
#     async def test_valid_delete_file_object(self, _):
#         test_echo = EchoInterface()

#         await test_echo.delete_file_object(self.test_image_path)
#         assert test_echo.bucket.Object.return_value.delete.call_count == 1

#     @pytest.mark.asyncio
#     @patch(
#         "operationsgateway_api.src.config.Config.config.echo.url",
#         config_echo_url,
#     )
#     @patch(
#         "operationsgateway_api.src.config.Config.config.echo.access_key",
#         config_echo_access_key,
#     )
#     @patch(
#         "operationsgateway_api.src.config.Config.config.echo.secret_key",
#         config_echo_secret_key,
#     )
#     @patch(
#         "operationsgateway_api.src.config.Config.config.echo.bucket_name",
#         config_image_bucket_name,
#     )
#     @patch("boto3.resource")
#     async def test_invalid_delete_file_object(self, _):
#         with patch("boto3.resource") as mock_resource:
#             mock_bucket = mock_resource.return_value.Bucket.return_value

#             mock_bucket.Object.return_value.delete.side_effect = ClientError(
#                 {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
#                 "delete",
#             )

#             test_echo = EchoInterface()

#             with pytest.raises(EchoS3Error, match="when deleting file at"):
#                 await test_echo.delete_file_object(self.test_image_path)

#         with patch("boto3.resource") as mock_resource:
#             mock_bucket = mock_resource.return_value.Bucket.return_value

#             mock_bucket.Object.return_value.load.side_effect = ClientError(
#                 {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
#                 "delete",
#             )

#             test_echo = EchoInterface()
#             with pytest.raises(EchoS3Error):
#                 await test_echo.delete_file_object(self.test_image_path)

#     @pytest.mark.asyncio
#     @patch(
#         "operationsgateway_api.src.config.Config.config.echo.url",
#         config_echo_url,
#     )
#     @patch(
#         "operationsgateway_api.src.config.Config.config.echo.access_key",
#         config_echo_access_key,
#     )
#     @patch(
#         "operationsgateway_api.src.config.Config.config.echo.secret_key",
#         config_echo_secret_key,
#     )
#     @patch(
#         "operationsgateway_api.src.config.Config.config.echo.bucket_name",
#         config_image_bucket_name,
#     )
#     @patch("boto3.resource")
#     async def test_valid_delete_directory(self, _):
#         test_echo = EchoInterface()
#         await test_echo.delete_directory("test/image/19900202143000/")
#         assert test_echo.bucket.objects.filter.return_value.delete.call_count == 1

#     @pytest.mark.asyncio
#     @patch(
#         "operationsgateway_api.src.config.Config.config.echo.url",
#         config_echo_url,
#     )
#     @patch(
#         "operationsgateway_api.src.config.Config.config.echo.access_key",
#         config_echo_access_key,
#     )
#     @patch(
#         "operationsgateway_api.src.config.Config.config.echo.secret_key",
#         config_echo_secret_key,
#     )
#     @patch(
#         "operationsgateway_api.src.config.Config.config.echo.bucket_name",
#         config_image_bucket_name,
#     )
#     @patch("boto3.resource")
#     async def test_invalid_delete_directory(self, _):
#         with patch("boto3.resource") as mock_resource:
#             mock_bucket = mock_resource.return_value.Bucket.return_value

#             mock_bucket.objects.filter.return_value.delete.side_effect = ClientError(
#                 {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
#                 "delete",
#             )

#             test_echo = EchoInterface()

#             with pytest.raises(EchoS3Error, match="when deleting directory"):
#                 await test_echo.delete_directory("test/image/19900202143000/")

#     @pytest.mark.asyncio
#     async def test_head_object(self):
#         echo_interface = EchoInterface()
#         assert not await echo_interface.head_object("test")
