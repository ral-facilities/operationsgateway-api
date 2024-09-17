from unittest.mock import patch

import pytest
import requests
from requests import ConnectionError, HTTPError, RequestException, Timeout

from operationsgateway_api.src.exceptions import ExperimentDetailsError
from operationsgateway_api.src.experiments.rest_error_handling import (
    rest_error_handling,
)


class TestRESTErrorHandling:
    @pytest.mark.parametrize(
        "raised_exception, expected_exception",
        [
            pytest.param(ConnectionError, ExperimentDetailsError, id="ConnectionError"),
            pytest.param(HTTPError(), ExperimentDetailsError, id="HTTPError"),
            pytest.param(Timeout(), ExperimentDetailsError, id="Timeout"),
            pytest.param(
                RequestException,
                ExperimentDetailsError,
                id="RequestException (base class for Requests exceptions)",
            ),
        ],
    )
    def test_correct_error_raised(self, raised_exception, expected_exception):
        @rest_error_handling("Testing")
        def raise_exception():
            with patch("requests.get", side_effect=raised_exception):
                requests.get("Test URL")

        with pytest.raises(expected_exception):
            raise_exception()
