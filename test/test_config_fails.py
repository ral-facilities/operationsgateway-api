import re

import pytest

from operationsgateway_api.src.config import APIConfig, ExperimentsConfig


class TestConfigFails:
    def test_failed_config_load(self):
        with pytest.raises(
            SystemExit,
            match=re.escape(
                "An error occurred while loading the config data: [Errno 2] No such "
                "file or directory: 'random_file.yml'",
            ),
        ):
            APIConfig.load(path="random_file.yml")

    def test_invalid_timezone(self):
        with pytest.raises(
            SystemExit,
            match="scheduler_background_timezone is not a valid timezone: Mars",
        ):
            ExperimentsConfig.check_timezone(value="Mars")
