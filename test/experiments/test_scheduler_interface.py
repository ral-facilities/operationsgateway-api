from unittest.mock import patch

from operationsgateway_api.src.experiments.scheduler_interface import SchedulerInterface


class TestSchedulerInterface:
    config_instrument_name = "Test Instrument"
    config_user_office_username = "Test Username"
    config_user_office_password = "Test Password"
    config_user_office_wsdl = "Test User Office URL"
    config_scheduler_wsdl = "Test Scheduler URL"

    @patch(
        "operationsgateway_api.src.experiments.scheduler_interface.SchedulerInterface"
        ".create_user_office_client",
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
    def test_init(self, _, mock_scheduler_client, mock_user_office_client):
        test_scheduler_interface = SchedulerInterface()

        assert mock_user_office_client.call_count == 1
        assert mock_scheduler_client.call_count == 1
        assert test_scheduler_interface.session_id == "Test Session ID"

    @patch(
        "operationsgateway_api.src.config.Config.config.experiments"
        ".user_office_wsdl_url",
        config_user_office_wsdl,
    )
    @patch("operationsgateway_api.src.experiments.scheduler_interface.Client")
    def test_create_user_office_client(self, mock_client):
        test_scheduler = object.__new__(SchedulerInterface)
        test_scheduler.create_user_office_client()

        assert mock_client.call_count == 1

        args = mock_client.call_args.args
        expected_args = (TestSchedulerInterface.config_user_office_wsdl,)
        assert args == expected_args

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

    @patch(
        "operationsgateway_api.src.config.Config.config.experiments.username",
        config_user_office_username,
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.experiments.password",
        config_user_office_password,
    )
    @patch(
        "operationsgateway_api.src.experiments.scheduler_interface.SchedulerInterface"
        ".create_user_office_client",
    )
    def test_login(self, _):
        test_scheduler = object.__new__(SchedulerInterface)
        test_scheduler.user_office_client = test_scheduler.create_user_office_client()

        with patch.object(test_scheduler, "user_office_client") as mock_client:
            test_scheduler.login()
            assert mock_client.service.login.call_count == 1

            args = mock_client.service.login.call_args.args
            expected_args = (
                TestSchedulerInterface.config_user_office_username,
                TestSchedulerInterface.config_user_office_password,
            )

            assert args == expected_args

    @patch(
        "operationsgateway_api.src.config.Config.config.experiments.instrument_name",
        config_instrument_name,
    )
    @patch(
        "operationsgateway_api.src.experiments.scheduler_interface.SchedulerInterface"
        ".create_user_office_client",
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
    def test_get_experiment_dates_for_instrument(self, _, __, ___):
        date_range = {
            "startDate": "2023-03-01T09:00:00",
            "endDate": "2023-03-02T09:00:00",
        }
        test_scheduler = SchedulerInterface()

        with patch.object(test_scheduler, "scheduler_client") as mock_client:
            test_scheduler.get_experiment_dates_for_instrument(
                date_range["startDate"],
                date_range["endDate"],
            )
            assert mock_client.service.getExperimentDatesForInstrument.call_count == 1

            args = mock_client.service.getExperimentDatesForInstrument.call_args.args
            expected_args = ("Test Session ID", "Test Instrument", date_range)
            assert args == expected_args

    @patch(
        "operationsgateway_api.src.experiments.scheduler_interface.SchedulerInterface"
        ".create_user_office_client",
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
    def test_get_experiments(self, _, __, ___):
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
