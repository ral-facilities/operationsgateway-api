from datetime import datetime
from http.client import IncompleteRead
import logging
from typing import List, Union

from pydantic import ValidationError
from suds import sudsobject
from suds import TypeNotFound, WebFault

from suds.client import Client

from operationsgateway_api.src.config import Config
from operationsgateway_api.src.exceptions import ExperimentDetailsError, ModelError
import operationsgateway_api.src.experiments.runners as runners
from operationsgateway_api.src.experiments.suds_error_handling import (
    suds_error_handling,
)
from operationsgateway_api.src.models import ExperimentModel
from operationsgateway_api.src.mongo.interface import MongoDBInterface
from operationsgateway_api.src.routes.common_parameters import ParameterHandler

log = logging.getLogger()


class Experiment:
    def __init__(self) -> None:
        try:
            log.info("Creating clients and logging into Scheduler")
            user_office_client = Client(
                Config.config.experiments.user_office_wsdl_url,
            )
            log.debug("Created user office client")
            self.scheduler_client = Client(
                Config.config.experiments.scheduler_wsdl_url,
            )
            log.debug("Scheduler client created")

            self.session_id = user_office_client.service.login(
                Config.config.experiments.username,
                Config.config.experiments.password,
            )
            log.debug("Session ID generated")
        except WebFault as exc:
            raise ExperimentDetailsError(
                "Problem processing current call: %s",
                str(exc),
            ) from exc
        except TypeNotFound as exc:
            raise ExperimentDetailsError(
                "WSDL call not constructed properly, could not be processed:"
                " %s",
                str(exc),
            ) from exc
        except IncompleteRead as exc:
            raise ExperimentDetailsError(
                "Incomplete HTTP read when contacting Scheduler",
            ) from exc

        self.experiments = []

    async def get_experiments_from_scheduler(self) -> None:
        """
        Get experiments from the scheduler (including start and end dates of each part)
        and store a list of experiments in a model, ready to go into MongoDB

        Only 4 entire experiments are called from the scheduler (2 seconds apart from
        each other) to avoid the scheduler returning an error

        TODO - docstring needs updating
        """

        log.info("Retrieving experiments from Scheduler")

        collection_last_updated = await self._get_collection_updated_date()
        experiment_search_start_date = (
            collection_last_updated
            if collection_last_updated
            else Config.config.experiments.first_scheduler_contact_start_date
        )
        experiment_search_end_date = runners.scheduler_runner.get_next_run_task_date()
        log.debug(
            "Parameters used for getExperimentDatesForInstrument(). Start date: %s, End"
            " date: %s",
            experiment_search_start_date,
            experiment_search_end_date,
        )

        # TODO - need exception handling on scheduler calls in case they go wrong
        log.info("Calling Scheduler getExperimentDatesForInstrument()")
        try:
            exp_data = self.scheduler_client.service.getExperimentDatesForInstrument(
                self.session_id,
                Config.config.experiments.instrument_name,
                {
                    "startDate": experiment_search_start_date,
                    "endDate": experiment_search_end_date,
                },
            )
        except WebFault as exc:
            raise ExperimentDetailsError(
                "Problem processing call to getExperimentDatesForInstrument: %s",
                str(exc),
            ) from exc
        except TypeNotFound as exc:
            raise ExperimentDetailsError(
                "WSDL call to getExperimentDatesForInstrument not constructed properly,"
                " could not be processed: "
                " %s",
                str(exc),
            ) from exc
        except IncompleteRead as exc:
            raise ExperimentDetailsError(
                "Incomplete HTTP read when contacting Scheduler. Occurred while"
                " calling getExperimentDatesForInstrument",
            ) from exc

        experiment_parts = self._map_experiments_to_part_numbers(exp_data)
        log.debug("Experiment parts: %s", experiment_parts)
        ids_for_scheduler_call = [
            {"key": experiment_id, "value": Config.config.experiments.instrument_name}
            for experiment_id in experiment_parts.keys()
        ]
        log.debug("Experiments to query for: %s", ids_for_scheduler_call)

        log.info("Calling Scheduler getExperiments()")
        try:
            experiments = self.scheduler_client.service.getExperiments(
                self.session_id,
                ids_for_scheduler_call,
            )
        except WebFault as exc:
            raise ExperimentDetailsError(
                "Problem processing call to getExperiments: %s",
                str(exc),
            ) from exc
        except TypeNotFound as exc:
            raise ExperimentDetailsError(
                "WSDL call to getExperiments not constructed properly,"
                " could not be processed: "
                " %s",
                str(exc),
            ) from exc
        except IncompleteRead as exc:
            raise ExperimentDetailsError(
                "Incomplete HTTP read when contacting Scheduler. Occurred while calling"
                " getExperiments",
            ) from exc

        self._extract_experiment_data(experiments, experiment_parts)

    async def store_experiments(self) -> None:
        """
        Store the experiments into MongoDB, using `upsert` to insert any experiments
        that haven't yet been inserted into the database
        """

        for experiment in self.experiments:
            await MongoDBInterface.update_one(
                "experiments",
                {"_id": experiment.id_},
                {"$set": experiment.dict(by_alias=True)},
                upsert=True,
            )

        await self._update_modification_time()

    def _map_experiments_to_part_numbers(
        self,
        experiments,
        # TODO - fix this type hint
        # experiments: List[sudsobject.experimentDateDTO],
    ) -> dict:
        """
        Extracts the rb number (experiment ID) and the experiment's part and puts them
        into a dictionary to get start and end dates for each one.

        Example output: {19510004: [1], 20310000: [1, 2, 3]}
        """

        exp_parts = {}

        for exp in experiments:
            try:
                exp_parts.setdefault(int(exp.rbNumber), []).append(exp.part)
            except AttributeError as exc:
                raise ExperimentDetailsError(str(exc)) from exc

        return exp_parts

    def _extract_experiment_data(self, experiments, experiment_part_mapping):
        """
        TODO - docstring and type hinting
        """

        for experiment in experiments:
            try:
                for part in experiment.experimentPartList:
                    if (
                        part.partNumber
                        in experiment_part_mapping[int(part.referenceNumber)]
                    ):
                        self.experiments.append(
                            ExperimentModel(
                                _id=f"{part.referenceNumber}-{part.partNumber}",
                                experiment_id=int(part.referenceNumber),
                                part=part.partNumber,
                                start_date=part.experimentStartDate,
                                end_date=part.experimentEndDate,
                            ),
                        )
            except AttributeError as exc:
                raise ExperimentDetailsError(str(exc)) from exc
            except ValidationError as exc:
                raise ModelError(str(exc)) from exc

    async def _update_modification_time(self) -> None:
        """
        TODO
        """

        await MongoDBInterface.update_one(
            "experiments",
            {"collection_last_updated": {"$exists": True}},
            {"$set": {"collection_last_updated": datetime.now()}},
            upsert=True,
        )

    async def _get_collection_updated_date(self) -> Union[datetime, None]:
        """
        TODO
        """

        collection_update_date = await MongoDBInterface.find_one(
            "experiments",
            filter_={"collection_last_updated": {"$exists": True}},
        )

        if collection_update_date:
            return collection_update_date["collection_last_updated"]
        else:
            # Get get_experiments_from_scheduler() to rely on a config setting as a
            # start date?
            return None

    @staticmethod
    async def get_experiments_from_database() -> List[dict]:
        """
        Get a list of experiments from the database, ordered by their ID.

        `_id` is the RB number and part number combined with a dash
        """

        experiments_query = MongoDBInterface.find(
            "experiments",
            filter_={"collection_last_updated": {"$exists": False}},
            sort=ParameterHandler.extract_order_data(["_id asc"]),
        )
        return await MongoDBInterface.query_to_list(experiments_query)
