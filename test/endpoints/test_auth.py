import base64
import json
import time

from fastapi.testclient import TestClient
import pytest


class TestAuth:
    @staticmethod
    def get_payload_dict_from_token(token: str) -> dict:
        # split the token into 3 parts
        token_parts = token.split(".")
        # the payload is the second part of the token between the first and second
        # "." characters
        # JWT tokens don't include padding characters for URL encoding reasons
        # so we need to add padding to keep the base64 library happy
        # see: https://stackoverflow.com/questions/2941995/
        token_payload_encoded = f"{token_parts[1]}=="
        json_payload = base64.b64decode(token_payload_encoded).decode()
        payload_dict = json.loads(json_payload)
        return payload_dict

    @pytest.mark.parametrize(
        "username, password, expected_response_code",
        [
            # backend and frontend are known "local" test users
            # and should log in successfully -> 200
            pytest.param(
                "backend",
                "back",
                200,
                id="Successful login by backend",
            ),
            pytest.param(
                "frontend",
                "front",
                200,
                id="Successful login by frontend",
            ),
            # users in this section have various problems with their database record
            # which result in DatabaseErrors and hence a 500 Server Error
            pytest.param(
                "invalid_auth_type_user",
                "password",
                500,
                id="Failed login by invalid_auth_type_user",
            ),
            pytest.param(
                "no_auth_type_user",
                "password",
                500,
                id="Failed login by no_auth_type_user",
            ),
            pytest.param(
                "local_user_no_password",
                "password",
                500,
                id="Failed login by local_user_no_password",
            ),
            # this user is not known to the system and hence results in a
            # 401 Unauthorized response
            pytest.param(
                "unknown_user",
                "password",
                401,
                id="Failed login by unknown_user",
            ),
        ],
    )
    def test_logins(
        self,
        test_app: TestClient,
        username,
        password,
        expected_response_code,
    ):
        login_response = test_app.post(
            "/login",
            content=json.dumps({"username": username, "password": password}),
        )

        assert login_response.status_code == expected_response_code

        if login_response.status_code == 200:
            # check that a valid access token was returned in the reponse
            access_token = login_response.text[1:-1]
            access_payload_dict = TestAuth.get_payload_dict_from_token(access_token)
            # check the username in the payload is correct
            assert access_payload_dict["username"] == username

            # check that a valid refresh token was returned in the header
            # first get the value of cookie being set up to the first semi-colon
            # which should be at the end of the JWT token. Value should be:
            # refresh_token=<header>.<payload>.<signature>
            set_cookie_value = login_response.headers["set-cookie"].split(";")[0]
            assert set_cookie_value[0:14] == "refresh_token="
            # the token itself is everything after the "="
            refresh_token = set_cookie_value.split("=")[1]
            refresh_payload_dict = TestAuth.get_payload_dict_from_token(refresh_token)
            # check the payload contains an expiry field
            assert "exp" in refresh_payload_dict
            # and that the refresh token is valid for longer than the access token
            assert refresh_payload_dict["exp"] > access_payload_dict["exp"]

            # validate the access token by passing it back to the server
            verify_response = test_app.post(
                "/verify",
                content=json.dumps({"token": access_token}),
            )
            assert verify_response.status_code == 200

            # refresh the access token using the refresh token
            # wait 2 seconds so that the expiry time on the refreshed token is later
            # than the expiry time on the original token
            time.sleep(2)
            refresh_response = test_app.post(
                "/refresh",
                content=json.dumps({"token": access_token}),
                headers={"Cookie": f"refresh_token={refresh_token}"},
            )
            assert refresh_response.status_code == 200
            new_access_token = refresh_response.text[1:-1]
            new_access_payload_dict = TestAuth.get_payload_dict_from_token(
                new_access_token,
            )
            assert new_access_payload_dict["username"] == username
            assert new_access_payload_dict["exp"] > access_payload_dict["exp"]
