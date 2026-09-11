import re

import pytest

from operationsgateway_api.src.config import APIConfig, ExperimentsConfig


class TestConfigFails:
    def test_invalid_timezone(self):
        with pytest.raises(
            SystemExit,
            match="scheduler_background_timezone is not a valid timezone: Mars",
        ):
            ExperimentsConfig.check_timezone(value="Mars")
