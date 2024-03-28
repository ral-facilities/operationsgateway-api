from unittest.mock import patch

import pytest

from operationsgateway_api.src.exceptions import ForbiddenError


class TestJwtHandler:
    def test_verify_token_fail(self, jwt_handler_instance):
        with pytest.raises(ForbiddenError, match="Invalid token"):
            jwt_handler_instance.verify_token("test_token")

    def test_refresh_token_blacklisted(self, jwt_handler_instance):
        with patch(
            "operationsgateway_api.src.auth.jwt_handler.JwtHandler."
            "get_blacklisted_tokens",
            return_value=["test_refresh_token"],
        ):
            with patch(
                "operationsgateway_api.src.auth.jwt_handler.JwtHandler.verify_token",
                return_value={"username": "test_user"},
            ):
                with pytest.raises(ForbiddenError, match="Token is blacklisted"):
                    jwt_handler_instance.refresh_token(
                        "test_refresh_token",
                        "test_access_token",
                    )

    def test_refresh_token_fail(self, jwt_handler_instance):
        with patch(
            "operationsgateway_api.src.auth.jwt_handler.JwtHandler.verify_token",
            return_value={"username": "test_user"},
        ):
            with pytest.raises(ForbiddenError, match="Unable to refresh token"):
                jwt_handler_instance.refresh_token(
                    "test_refresh_token",
                    "test_access_token",
                )

    def test_get_blacklisted_tokens(
        self,
        jwt_handler_instance,
        create_temp_blacklisted_token_file,
    ):
        # create a test file in the parent.x3 and rename the filename then delete it
        # (info on slack)

        with patch(
            "operationsgateway_api.src.auth.jwt_handler.JwtHandler.blacklisted_tokens_filename",
            new="temp_blacklisted_test_tokens.txt",
        ):
            return_value = jwt_handler_instance.get_blacklisted_tokens()

        assert return_value == ["test_token1", "test_token2", "test_token3"]


# perhaps move the file opening into a seperate function that can easily be mocked?
# or is it that changing any original file is bad
