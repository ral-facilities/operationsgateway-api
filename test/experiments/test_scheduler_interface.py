from unittest.mock import patch

import pytest

from operationsgateway_api.src.exceptions import ExperimentDetailsError
from operationsgateway_api.src.experiments.scheduler_interface import SchedulerInterface


class TestSchedulerInterface:
    config_instrument_names = ["Test Instrument", "Test Instrument #2"]
    config_scheduler_wsdl = "Test Scheduler URL"

    @patch(
        "operationsgateway_api.src.experiments.scheduler_interface.SchedulerInterface"
        ".create_scheduler_client",
    )
    @patch(
        "operationsgateway_api.src.experiments.scheduler_interface.SchedulerInterface"
        ".login",
        return_value="Test Session ID",
    )
    def test_init(self, _, mock_scheduler_client):
        test_scheduler_interface = SchedulerInterface()

        assert mock_scheduler_client.call_count == 1
        assert test_scheduler_interface.session_id == "Test Session ID"

    @patch(
        "operationsgateway_api.src.config.Config.config.experiments.scheduler_wsdl_url",
        config_scheduler_wsdl,
    )
    @patch("operationsgateway_api.src.experiments.scheduler_interface.Client")
    def test_create_scheduler_client(self, mock_client):
        test_scheduler = object.__new__(SchedulerInterface)
        test_scheduler.create_scheduler_client()

        assert mock_client.call_count == 1

        args = mock_client.call_args.args
        expected_args = (TestSchedulerInterface.config_scheduler_wsdl,)
        assert args == expected_args

    @patch("requests.post")
    def test_valid_login(self, mock_user_office_login):
        mock_user_office_login.return_value.status_code = 201
        mock_session_id = "abc1254d-3c54-321a-abc9-a8765b43cd21"
        mock_user_office_login.return_value.json.return_value = {
            "userId": "1127868",
            "sessionId": mock_session_id,
            "lastAccessTime": "2024-08-14T08:00:00+01:00",
            "loginType": "DATABASE",
            "comments": None,
        }

        # Use object.__new__ so __init__() doesn't run. We don't want to run that as
        # we're only testing login()
        test_scheduler = object.__new__(SchedulerInterface)
        session_id = test_scheduler.login()
        assert session_id == mock_session_id

    @patch("requests.post")
    @pytest.mark.parametrize(
        "mock_status_code, mock_json_response",
        [
            pytest.param(
                401,
                {
                    "shortcode": "Unauthorized",
                    "reason": "Authorization details were wrong",
                    "details": ["Specified username or password was incorrect"],
                },
                id="Incorrect credentials",
            ),
            pytest.param(
                201,
                {
                    "userId": "1127868",
                    "lastAccessTime": "2024-08-14T08:00:00+01:00",
                    "loginType": "DATABASE",
                    "comments": None,
                },
                id="Missing session ID",
            ),
        ],
    )
    def test_invalid_login(
        self,
        mock_user_office_login,
        mock_status_code,
        mock_json_response,
    ):
        mock_user_office_login.return_value.status_code = mock_status_code
        mock_user_office_login.return_value.json.return_value = mock_json_response

        with pytest.raises(ExperimentDetailsError):
            # Use object.__new__ so __init__() doesn't run. We don't want to run that as
            # we're only testing login()
            test_scheduler = object.__new__(SchedulerInterface)
            test_scheduler.login()

    @patch(
        "operationsgateway_api.src.config.Config.config.experiments.instrument_names",
        config_instrument_names,
    )
    @patch(
        "operationsgateway_api.src.experiments.scheduler_interface.SchedulerInterface"
        ".create_scheduler_client",
    )
    @patch(
        "operationsgateway_api.src.experiments.scheduler_interface.SchedulerInterface"
        ".login",
        return_value="Test Session ID",
    )
    def test_get_experiment_dates_for_instrument(self, _, __):
        date_range = {
            "startDate": "2023-03-01T09:00:00",
            "endDate": "2023-03-02T09:00:00",
        }
        test_scheduler = SchedulerInterface()

        with patch.object(test_scheduler, "scheduler_client") as mock_client:
            test_scheduler.get_experiment_dates_for_instrument(
                self.config_instrument_names[0],
                date_range["startDate"],
                date_range["endDate"],
            )
            assert mock_client.service.getExperimentDatesForInstrument.call_count == 1

            args = mock_client.service.getExperimentDatesForInstrument.call_args.args
            expected_args = ("Test Session ID", "Test Instrument", date_range)
            assert args == expected_args

    @patch(
        "operationsgateway_api.src.experiments.scheduler_interface.SchedulerInterface"
        ".create_scheduler_client",
    )
    @patch(
        "operationsgateway_api.src.experiments.scheduler_interface.SchedulerInterface"
        ".login",
        return_value="Test Session ID",
    )
    def test_get_experiments(self, _, __):
        id_instrument_pairs = [
            {"key": 12345678, "value": "Test Instrument Name"},
            {"key": 23456789, "value": "Test Instrument Name"},
        ]
        test_scheduler = SchedulerInterface()

        with patch.object(test_scheduler, "scheduler_client") as mock_client:
            test_scheduler.get_experiments(id_instrument_pairs)
            assert mock_client.service.getExperiments.call_count == 1

            args = mock_client.service.getExperiments.call_args.args
            expected_args = ("Test Session ID", id_instrument_pairs)
            assert args == expected_args
