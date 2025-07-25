from unittest.mock import MagicMock, patch

import jwt
import pytest

from operationsgateway_api.src.auth.oidc_handler import OidcHandler
from operationsgateway_api.src.exceptions import AuthServerError


class TestOidcHandler:
    _issuer = "http://localhost:8081/realms/testrealm"
    _kid = "dZqu2hFr2k6SB5I36lv84ZNSVw38PKbYDlUoPpgk8WQ"
    _audience = "operations-gateway"
    _claim = "email"
    _email_value = "test@example.ac.uk"

    @pytest.fixture()
    def handler_with_mocked_provider(self):
        key = MagicMock()
        key.algorithm_name = "RS256"

        provider = MagicMock()
        provider.get_key.return_value = key
        provider.get_issuer.return_value = self._issuer
        provider.get_audience.return_value = self._audience
        provider.get_matching_claim.return_value = self._claim

        handler = OidcHandler.__new__(OidcHandler)
        handler._providers = {self._issuer: provider}
        return handler

    expired_token = (
        "eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICIzT0lkZW1"
        "mU0pIQ1dFU0RlTGE3Q2xvdjNFeEdQa1F2a0Z0a0x2VUp4a1ZVIn0.eyJle"
        "HAiOjE3NTMyODY4NDEsImlhdCI6MTc1MzI4NjU0MSwiYXV0aF90aW1lIjo"
        "wLCJqdGkiOiJjZGE4YzJkZi01NTExLTQ1ZjUtYjA3Ni02OWViZDY2NjU3M"
        "jAiLCJpc3MiOiJodHRwOi8vbG9jYWxob3N0OjgwODEvcmVhbG1zL3Rlc3R"
        "yZWFsbSIsImF1ZCI6Im9wZXJhdGlvbnMtZ2F0ZXdheSIsInN1YiI6IjIyY"
        "zY0NjZmLTI1OWMtNDI0Ny1iODY0LWQ1ZjAyYWI0ODg3MyIsInR5cCI6Ikl"
        "EIiwiYXpwIjoib3BlcmF0aW9ucy1nYXRld2F5Iiwic2Vzc2lvbl9zdGF0Z"
        "SI6ImQyYWYyOWZhLTlmZGUtNDNlYi1hZDUyLThmYjZjM2IxMTk1NSIsIm"
        "F0X2hhc2giOiJmUmJhRGF0UE55N004SnUxbG5aS1d3Iiwic2lkIjoiZDJ"
        "hZjI5ZmEtOWZkZS00M2ViLWFkNTItOGZiNmMzYjExOTU1IiwiZW1haWxf"
        "dmVyaWZpZWQiOnRydWUsImdpdmVuX25hbWUiOiJBbGljZSIsImZhbWlse"
        "V9uYW1lIjoiRXhhbXBsZSIsImVtYWlsIjoidGVzdEBleGFtcGxlLmFjLn"
        "VrIn0.clht0467zTn0pAJiDt3qWq_DIHd02cN4OtEcD2J4KbQ0VmF2VAm"
        "PHHETp_i812uRUoSGqy3_AEgQx6GZPNF0B-3OYm54YBq27N_9t2woa9IF"
        "rQtn6uMT_4XqWTce04MuveAIQKFJoAYy69_kuGguFVq5HOF4__DV2HYDy"
        "pFtxZkOQ91_dq_vbK9UE5tum_AIwGfCJFkayo1grQvxERi-YbUb6yeOYKO"
        "3TrtP2CqF3kUALesTQJl6YMq7l9xAPZxhRiyj95uDVE0Xrz5yp41_GmYP1"
        "SxOmHZn6PS2G0qnScnlaWPgKIuRrtukFhxyBqY2AUPKHlOMqKcUSp5N0A"
        "_9vQ"
    )

    def test_oidc_handler_rejects_expired_token(
        self,
        handler_with_mocked_provider,
    ):
        """Check that expired token raises AuthServerError with specific message."""
        with patch("jwt.get_unverified_header") as mock_header, patch(
            "jwt.decode",
        ) as mock_decode:
            mock_header.return_value = {"kid": self._kid}
            # First decode returns payload with issuer
            mock_decode.side_effect = [
                {"iss": self._issuer},
                jwt.exceptions.ExpiredSignatureError("Token has expired"),
            ]

            with pytest.raises(AuthServerError) as exc_info:
                handler_with_mocked_provider.handle(self.expired_token)

            assert str(exc_info.value) == "OIDC token has expired"

    def test_oidc_handler_decodes_and_extracts_claim(
        self,
        handler_with_mocked_provider,
    ):
        """Check that the email claim is extracted when expiry/signature
        checks are skipped."""
        with patch("jwt.get_unverified_header") as mock_header, patch(
            "jwt.decode",
        ) as mock_decode:

            mock_header.return_value = {"kid": self._kid}
            # First decode returns payload with issuer
            mock_decode.side_effect = [
                {"iss": self._issuer},
                {
                    "email": self._email_value,
                    "aud": self._audience,
                    "exp": 0,
                },
            ]

            result = handler_with_mocked_provider.handle(self.expired_token)
            assert result == self._email_value
