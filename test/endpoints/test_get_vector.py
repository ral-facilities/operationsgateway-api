import json
from urllib.parse import quote

from fastapi.testclient import TestClient
import pytest


class TestGetWaveformByID:
    def test_get_vector(
        self,
        test_app: TestClient,
        login_and_get_token,
    ):

        test_response = test_app.get(
            "/vectors/20230605080300/CM-202-CVC-WFS-COEF",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_response.status_code == 200

        data = [
            5.639372695195284,
            5.587336765253104,
            1.826101240997037,
            2.521215679028282,
            -2.980784658113992,
            -2.279530101757219,
            0.8275213451146765,
            -0.2507684324157028,
            -1.3952389582428177,
            -0.925578472683586,
            0.5665629489813115,
            0.6252987786682547,
            0.16671172514266414,
            0.0724989856677573,
            0.18313006266485013,
            0.26288446058591775,
            -0.03412582732888118,
            0.1467799869560521,
            0.16014661721357387,
            0.10650232684232015,
        ]
        assert test_response.json() == {"data": data}

    def test_get_vector_failure(
        self,
        test_app: TestClient,
        login_and_get_token,
    ):

        test_response = test_app.get(
            "/vectors/20230605080300/test",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_response.status_code == 500
        assert test_response.json()["detail"] == (
            "Vector could not be found on object storage: 2023/06/05/080300/test.json"
        )
