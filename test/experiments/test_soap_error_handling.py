import pytest
from zeep.exceptions import (
    DTDForbidden,
    EntitiesForbidden,
    Error,
    Fault,
    TransportError,
    ValidationError,
    XMLParseError,
)

from operationsgateway_api.src.exceptions import ExperimentDetailsError
from operationsgateway_api.src.experiments.soap_error_handling import soap_error_handling


class TestSoapErrorHandling:
    @pytest.mark.parametrize(
        "raised_exception, expected_exception",
        [
            pytest.param(Fault, ExperimentDetailsError, id="Fault"),
            pytest.param(TransportError, ExperimentDetailsError, id="TransportError"),
            pytest.param(XMLParseError, ExperimentDetailsError, id="XMLParseError"),
            pytest.param(ValidationError, ExperimentDetailsError, id="ValidationError"),
            pytest.param(DTDForbidden("Test error message", 123, 456), ExperimentDetailsError, id="DTDForbidden"),
            pytest.param(
                EntitiesForbidden("Test error message", "content"), ExperimentDetailsError, id="EntitiesForbidden",
            ),
            pytest.param(Error, ExperimentDetailsError, id="Error"),
        ],
    )
    def test_correct_error_raised(self, raised_exception, expected_exception):
        @soap_error_handling("Testing")
        def raise_exception():
            if isinstance(raised_exception, DTDForbidden) or isinstance(raised_exception, EntitiesForbidden):
                # Additional arguments are needed for these exceptions, which are
                # provided in the pytest parameters for this tests
                raise raised_exception
            else:
                raise raised_exception("Test error message")

        with pytest.raises(expected_exception):
            raise_exception()
