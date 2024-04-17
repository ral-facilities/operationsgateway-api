import pytest

from operationsgateway_api.src.auth.auth_keys import get_private_key, get_public_key
from operationsgateway_api.src.config import Config


class TestKeyRetrieval:
    def test_private_key_fail(self, monkeypatch):
        monkeypatch.setattr(
            Config.config.auth,
            "private_key_path",
            "/nonexistent/path/private_key.pem",
        )
        with pytest.raises(SystemExit):
            get_private_key()

    def test_public_key_fail(self, monkeypatch):
        monkeypatch.setattr(
            Config.config.auth,
            "public_key_path",
            "/nonexistent/path/public_key.pem",
        )
        with pytest.raises(SystemExit):
            get_public_key()
