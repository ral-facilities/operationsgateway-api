from datetime import datetime
import json
import logging
from typing import Dict, List, Union

import requests
from zeep import Client

from operationsgateway_api.src.config import Config
from operationsgateway_api.src.exceptions import ExperimentDetailsError
from operationsgateway_api.src.experiments.rest_error_handling import (
    rest_error_handling,
)
from operationsgateway_api.src.experiments.soap_error_handling import (
    soap_error_handling,
)

log = logging.getLogger()


class SchedulerInterface:
    """
    An implementation of the ISIS Scheduler system to interface between
    OperationsGateway and their Scheduler system. This class also includes some error
    handling for the calls to the Scheduler too
    """

    login_endpoint_name = "/sessions"

    def __init__(self) -> None:
        self.scheduler_client = self.create_scheduler_client()
        self.session_id = self.login()

    @soap_error_handling("create scheduler client")
    def create_scheduler_client(self) -> Client:
        log.info("Creating scheduler client")
        return Client(Config.config.experiments.scheduler_wsdl_url)

    @rest_error_handling(login_endpoint_name)
    def login(self) -> str:
        log.info("Generating session ID for Scheduler system")
        credentials = {
            "username": Config.config.experiments.username,
            "password": Config.config.experiments.password.get_secret_value(),
        }
        headers = {"Content-Type": "application/json"}

        login_response = requests.post(
            f"{Config.config.experiments.user_office_rest_api_url}"
            f"{SchedulerInterface.login_endpoint_name}",
            data=json.dumps(credentials),
            headers=headers,
        )
        if login_response.status_code != 201:
            log.error("Request response: %s", login_response.json())
            raise ExperimentDetailsError(
                "Logging in to retrieve experiments wasn't successful. %s recieved",
                login_response.status_code,
            )
        try:
            session_id = login_response.json()["sessionId"]
        except KeyError as exc:
            log.error("Status code from POST /sessions: %s", login_response.status_code)
            log.error("Request response: %s", login_response.json())
            raise ExperimentDetailsError(
                "Session ID cannot be found from User Office API login endpoint",
            ) from exc

        return session_id

    @soap_error_handling("getExperimentDatesForInstrument")
    def get_experiment_dates_for_instrument(
        self,
        instrument_name: str,
        start_date: datetime,
        end_date: datetime,
    ) -> list:
        """
        Get a list of experiments (for a given instrument) that are between two dates
        """
        log.info("Calling Scheduler getExperimentDatesForInstrument()")
        return self.scheduler_client.service.getExperimentDatesForInstrument(
            self.session_id,
            instrument_name,
            {
                "startDate": start_date,
                "endDate": end_date,
            },
        )

    @soap_error_handling("getExperiments")
    def get_experiments(
        self,
        id_instrument_pairs: List[Dict[str, Union[str, int]]],
    ) -> list:
        """
        Get details of multiple experiments by providing a list of experiment ID,
        instrument name pairs
        """
        log.info("Calling Scheduler getExperiments()")
        return self.scheduler_client.service.getExperiments(
            self.session_id,
            id_instrument_pairs,
        )
