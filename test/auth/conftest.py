import os

import pytest

from operationsgateway_api.src.auth.jwt_handler import JwtHandler
from operationsgateway_api.src.models import UserModel


@pytest.fixture
def jwt_handler_instance():
    test_user = UserModel(_id="Test User", auth_type="Test")
    return JwtHandler(test_user)


@pytest.fixture
def create_temp_blacklisted_token_file():
    file_content = "test_token1\ntest_token2\ntest_token3"
    file_name = "operationsgateway_api/temp_blacklisted_test_tokens.txt"

    with open(file_name, "w") as file:
        file.write(file_content)

    yield

    os.remove(file_name)
