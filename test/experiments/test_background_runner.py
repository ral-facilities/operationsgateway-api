from datetime import datetime
from unittest.mock import patch

import pytest

from operationsgateway_api.src.exceptions import ExperimentDetailsError
from operationsgateway_api.src.experiments.background_scheduler_runner import (
    BackgroundSchedulerRunner,
)


class TestBackgroundRunner:
    def create_background_runner(self):
        test_task_name = "Test Task"
        test_runner = BackgroundSchedulerRunner(test_task_name)
        return test_runner

    def test_task_name(self):
        test_runner = self.create_background_runner()
        assert test_runner.task_name == "Test Task"

    @pytest.mark.parametrize(
        "cron_string",
        [
            pytest.param("0 9 * * 1", id="Every Monday at 09:00"),
            pytest.param("* * * * *", id="Every minute of every day"),
            pytest.param("30 20 1 * *", id="First day of each month at 20:30"),
        ],
    )
    def test_valid_task_frequency(self, cron_string):
        # Can't patch via decorator as this uses `cron_string` parameter
        with patch(
            "operationsgateway_api.src.config.Config.config.experiments"
            ".scheduler_background_frequency",
            cron_string,
        ):
            test_runner = self.create_background_runner()
            assert test_runner.runner_timer.to_string() == cron_string

    @pytest.mark.parametrize(
        "cron_string, expected_exception",
        [
            pytest.param("0 9 **1", ValueError, id="Too few spaces in cron string"),
            pytest.param("09**1", ValueError, id="No spaces in cron string"),
            pytest.param(
                "* * * * * *",
                ValueError,
                id="Too many digits in cron string",
            ),
            pytest.param("Invalid cron string", ValueError, id="Invalid string input"),
            pytest.param(1234, TypeError, id="Integer input"),
            pytest.param(True, TypeError, id="Boolean input"),
            pytest.param(234.56, TypeError, id="Float input"),
        ],
    )
    def test_invalid_task_frequency(self, cron_string, expected_exception):
        with patch(
            "operationsgateway_api.src.config.Config.config.experiments"
            ".scheduler_background_frequency",
            cron_string,
        ):
            with pytest.raises(expected_exception):
                self.create_background_runner()

    # Builtins written in C cannot be directed patched, you have to patch the module
    # that it's being used in. See 'Partial mocking' in the unittest.mocking
    # documentation
    @patch("cron_converter.sub_modules.seeker.datetime")
    @pytest.mark.parametrize(
        "cron_string, expected_next_run_date",
        [
            pytest.param(
                "0 15 * * *",
                datetime.fromisoformat("2023-03-01T15:00:00"),
                id="Simple daily use case",
            ),
            pytest.param(
                "0 9 * * 1",
                datetime.fromisoformat("2023-03-06T09:00:00"),
                id="Simple weekly use case",
            ),
            pytest.param(
                "0 15 20 * *",
                datetime.fromisoformat("2023-03-20T15:00:00"),
                id="Simple monthly use case",
            ),
            pytest.param(
                "0 4 1 * *",
                datetime.fromisoformat("2023-04-01T04:00:00"),
                id="Monthly check where check has already passed for current month",
            ),
        ],
    )
    def test_get_next_task_date(
        self,
        mock_datetime,
        cron_string,
        expected_next_run_date,
    ):
        mock_datetime.now.return_value = datetime.fromisoformat("2023-03-01T08:00:00")
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

        with patch(
            "operationsgateway_api.src.config.Config.config.experiments"
            ".scheduler_background_frequency",
            cron_string,
        ):
            test_runner = self.create_background_runner()
            next_run_date = test_runner.get_next_run_task_date()
            assert next_run_date == expected_next_run_date

    @patch("cron_converter.sub_modules.seeker.datetime")
    @patch("operationsgateway_api.src.experiments.background_scheduler_runner.datetime")
    @pytest.mark.parametrize(
        "cron_string, expected_wait_time",
        [
            pytest.param("0 15 * * *", 25200, id="Daily check"),
            pytest.param("0 10 * * 1", 439200, id="Weekly check"),
            pytest.param("0 10 28 * *", 2340000, id="Monthly check"),
            pytest.param(
                "0 10 * 4 1",
                2858400,
                id="Edge case check for the next month",
            ),
            pytest.param(
                "0 10 * 10 1",
                18583200,
                id="Extreme case check that won't run for 7 months",
            ),
        ],
    )
    def test_get_wait_interval(
        self,
        mock_runner_datetime,
        mock_seeker_datetime,
        cron_string,
        expected_wait_time,
    ):
        mock_runner_datetime.now.return_value = datetime.fromisoformat(
            "2023-03-01T08:00:00+00:00",
        )
        mock_runner_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        mock_seeker_datetime.now.return_value = datetime.fromisoformat(
            "2023-03-01T08:00:00+00:00",
        )
        mock_seeker_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

        with patch(
            "operationsgateway_api.src.config.Config.config.experiments"
            ".scheduler_background_frequency",
            cron_string,
        ):
            test_runner = self.create_background_runner()
            wait_seconds = test_runner._get_wait_interval()

            assert wait_seconds == expected_wait_time

    @pytest.mark.asyncio
    @patch(
        "operationsgateway_api.src.experiments.background_scheduler_runner"
        ".BackgroundSchedulerRunner._get_wait_interval",
        return_value=0.1,
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.experiments"
        ".scheduler_background_retry_mins",
        0.01,
    )
    @patch(
        "operationsgateway_api.src.experiments.experiment.Experiment.__init__",
        side_effect=ExperimentDetailsError("Mocked Exception"),
    )
    @patch(
        "operationsgateway_api.src.experiments.background_scheduler_runner.log.error",
        return_value=True,
    )
    @patch("asyncio.sleep")
    async def test_task_retry(self, mock_sleep, _, mock_experiment, __):
        test_runner = self.create_background_runner()
        await test_runner.start_task()
        assert mock_experiment.call_count == 2
        assert mock_sleep.call_count == 2
