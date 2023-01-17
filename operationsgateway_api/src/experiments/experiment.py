from datetime import datetime
import logging
from typing import List, Union

from suds import sudsobject
from suds.client import Client

from operationsgateway_api.src.config import Config
from operationsgateway_api.src.models import ExperimentModel
from operationsgateway_api.src.mongo.interface import MongoDBInterface
from operationsgateway_api.src.routes.common_parameters import ParameterHandler

log = logging.getLogger()


class Experiment:
    def __init__(self) -> None:
        # TODO - think some client handling might be needed here, so the same client
        # can be used throughout the lifetime of the instance. Would something as simple
        # as class vars work?
        user_office_client = Client(
            Config.config.experiments.user_office_wsdl_url,
        )
        self.session_id = user_office_client.service.login(
            Config.config.experiments.username,
            Config.config.experiments.password,
        )
        self.scheduler_client = Client(
            Config.config.experiments.scheduler_wsdl_url,
        )

        self.experiments = []

    async def get_experiments_from_scheduler(self) -> None:
        """
        Get experiments from the scheduler (including start and end dates of each part)
        and store a list of experiments in a model, ready to go into MongoDB

        Only 4 entire experiments are called from the scheduler (2 seconds apart from
        each other) to avoid the scheduler returning an error
        """

        # TODO - this needs to be a background task as well as a specific endpoint

        collection_last_updated = await self.get_collection_updated_date()
        experiment_search_start_date = (
            collection_last_updated
            if collection_last_updated
            else "2019-01-01T00:00:00Z"
        )
        print(f"Proposed start date: {experiment_search_start_date}")

        # Turning Black formatter off to avoid `experiments_data` turning into a tuple
        # fmt: off
        experiments_data = self.scheduler_client.service.getExperimentDatesForInstrument(  # noqa: B950
            self.session_id,
            Config.config.experiments.instrument_name,
            {
                "startDate": experiment_search_start_date,
                "endDate": datetime.now(),
            },
        )
        # fmt: on

        experiment_parts = self._map_experiments_to_part_numbers(experiments_data)
        ids_for_scheduler_call = [
            {"key": experiment_id, "value": Config.config.experiments.instrument_name}
            for experiment_id in experiment_parts.keys()
        ]

        experiments = self.scheduler_client.service.getExperiments(
            self.session_id,
            ids_for_scheduler_call,
        )

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

        await self.update_modification_time()

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
            # TODO - try/except AttributeError needed here
            exp_parts.setdefault(int(exp.rbNumber), []).append(exp.part)

        return exp_parts

    def _extract_experiment_data(self, experiments, experiment_part_mapping):
        for experiment in experiments:
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

    async def update_modification_time(self) -> None:
        """
        TODO
        """

        await MongoDBInterface.update_one(
            "experiments",
            {"collection_last_updated": {"$exists": True}},
            {"$set": {"collection_last_updated": datetime.now()}},
            upsert=True,
        )

    async def get_collection_updated_date(self) -> Union[datetime, None]:
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
