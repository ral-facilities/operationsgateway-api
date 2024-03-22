from datetime import datetime
from unittest.mock import patch

from fastapi.testclient import TestClient
import pytest

from test.experiments.scheduler_mocking.experiments_mocks import get_experiments_mock
from test.experiments.scheduler_mocking.get_exp_dates_mocks import general_mock


class TestPostExperiments:
    config_instrument_names = ["Test Instrument", "Test Instrument #2"]
    config_scheduler_contact_date = datetime(2023, 3, 2, 10, 0)
    experiment_search_start_date = "2020-01-01T00:00:00Z"
    experiment_search_end_date = "2020-05-01T00:00:00Z"

    @patch(
        "operationsgateway_api.src.experiments.scheduler_interface.SchedulerInterface"
        ".__init__",
        return_value=None,
    )
    @patch(
        "operationsgateway_api.src.experiments.experiment.Experiment"
        "._get_collection_updated_date",
        return_value=datetime(2023, 3, 1, 10, 0),
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.experiments"
        ".first_scheduler_contact_start_date",
        config_scheduler_contact_date,
    )
    @patch(
        "operationsgateway_api.src.experiments.background_scheduler_runner"
        ".BackgroundSchedulerRunner.get_next_run_task_date",
        return_value=datetime(2023, 3, 10, 10, 0),
    )
    @patch(
        "operationsgateway_api.src.experiments.scheduler_interface.SchedulerInterface"
        ".get_experiment_dates_for_instrument",
        return_value=general_mock,
    )
    @patch(
        "operationsgateway_api.src.experiments.scheduler_interface"
        ".SchedulerInterface.get_experiments",
        return_value=get_experiments_mock(
            {20310001: [1, 2, 3], 18325019: [4], 20310002: [1]},
            return_duplicate_parts=True,
        ),
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.experiments.instrument_names",
        config_instrument_names,
    )
    @pytest.mark.asyncio
    async def test_store_experiments(
        self,
        _,
        __,
        ___,
        ____,
        _____,
        test_app: TestClient,
        login_and_get_token,
    ):

        test_response = test_app.post(
            "/experiments",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_response.status_code == 200
        assert (
            test_response.text
            == '["Updated 65fbf893a4aa1ab48a5f381f","Updated 65fbf893a4aa1ab48a5f3821"'
            ',"Updated 65fbf893a4aa1ab48a5f3823","Updated 65fbf893a4aa1ab48a5f3815",'
            '"Updated 65fd555b437c051568c731db"]'
        )
