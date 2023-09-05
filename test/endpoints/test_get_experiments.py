import os

from fastapi.testclient import TestClient
import pytest


class TestGetExperiments:
    @pytest.mark.skipif(
        os.environ.get("GITHUB_ACTIONS") == "true",
        reason="Scheduler can't be accessed on GitHub Actions so no experiments"
        " will exist",
    )
    def test_get_experiments(self, test_app: TestClient, login_and_get_token):
        # There are quite a few experiments and the experiments rely on the data from
        # the dev Scheduler (which could change). Therefore I think it's better to check
        # just a few experiments and ensure they're correct, rather than checking every
        # single experiment
        expected_experiments_snippet = [
            {
                "end_date": "2020-01-06T18:00:00",
                "experiment_id": "18325019",
                "part": 4,
                "start_date": "2020-01-03T10:00:00",
            },
            {
                "end_date": "2019-06-12T17:00:00",
                "experiment_id": "18325019",
                "part": 5,
                "start_date": "2019-06-12T09:00:00",
            },
            {
                "end_date": "2020-02-24T18:00:00",
                "experiment_id": "20310001",
                "part": 1,
                "start_date": "2020-02-24T10:00:00",
            },
        ]

        test_response = test_app.get(
            "/experiments",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )
        assert test_response.status_code == 200

        test_experiments = test_response.json()

        for expected_experiment in expected_experiments_snippet:
            experiment_found = False
            for experiment in test_experiments:
                if (
                    experiment["experiment_id"] == expected_experiment["experiment_id"]
                    and experiment["part"] == expected_experiment["part"]
                ):
                    experiment_found = True

                    try:
                        # _id is an object ID so cannot be asserted against
                        del experiment["_id"]
                    except KeyError:
                        pass

                    assert experiment == expected_experiment
                    break

            if not experiment_found:
                raise AssertionError("Expected experiment not found")
