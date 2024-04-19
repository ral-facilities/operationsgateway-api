from datetime import datetime
from unittest.mock import patch

from fastapi.testclient import TestClient
import pytest

from operationsgateway_api.src.mongo.interface import MongoDBInterface
from test.experiments.scheduler_mocking.get_exp_dates_mocks import general_mock
from test.experiments.scheduler_mocking.models import ExperimentDTO, ExperimentPartDTO


class TestPostExperiments:
    config_instrument_names = ["Test Instrument", "Test Instrument #2"]
    config_scheduler_contact_date = datetime(2023, 3, 2, 10, 0)

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
        return_value=[
            ExperimentDTO(
                experimentPartList=[
                    ExperimentPartDTO(
                        experimentEndDate=datetime(1920, 4, 30, 18, 0),
                        experimentStartDate=datetime(1920, 4, 30, 10, 0),
                        partNumber=1,
                        referenceNumber="20310001",
                        status="Delivered",
                    ),
                ],
            ),
        ],
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
        remove_experiment_fixture,
    ):

        test_response = test_app.post(
            "/experiments",
            headers={"Authorization": f"Bearer {login_and_get_token}"},
        )

        assert test_response.status_code == 200

        experiment = await MongoDBInterface.find_one(
            "experiments",
            filter_={
                "experiment_id": "20310001",
                "start_date": datetime(1920, 4, 30, 10, 0),
            },
        )

        assert experiment is not None
