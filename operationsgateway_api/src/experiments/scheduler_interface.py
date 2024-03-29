from datetime import datetime
import logging
from typing import Dict, List, Union

from zeep import Client

from operationsgateway_api.src.config import Config
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

    def __init__(self) -> None:
        self.user_office_client = self.create_user_office_client()
        self.scheduler_client = self.create_scheduler_client()
        self.session_id = self.login()

    @soap_error_handling("create user office client")
    def create_user_office_client(self) -> Client:
        log.info("Creating user office client")
        return Client(Config.config.experiments.user_office_wsdl_url)

    @soap_error_handling("create scheduler client")
    def create_scheduler_client(self) -> Client:
        log.info("Creating scheduler client")
        return Client(Config.config.experiments.scheduler_wsdl_url)

    @soap_error_handling("login")
    def login(self) -> str:
        log.info("Generating session ID for Scheduler system")
        return self.user_office_client.service.login(
            Config.config.experiments.username,
            Config.config.experiments.password,
        )

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
