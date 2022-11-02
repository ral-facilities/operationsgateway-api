from pprint import pprint
from time import sleep
from typing import List

from suds.client import Client
from suds import sudsobject

from operationsgateway_api.src.config import Config
from operationsgateway_api.src.models import Experiment as ExperimentModel
from operationsgateway_api.src.mongo.interface import MongoDBInterface
from operationsgateway_api.src.routes.common_parameters import ParameterHandler

class Experiment:
    def __init__(self) -> None:
        user_office_client = Client(
            Config.config.experiments.user_office_wsdl_url,
        )
        self.session_id = user_office_client.service.login(
            Config.config.experiments.username, Config.config.experiments.password,
        )
        self.scheduler_client = Client(
            Config.config.experiments.scheduler_wsdl_url,
        )

        self.experiments = []
    
    def extract_experiment_part_numbers(self, experiments: List[sudsobject.experimentDateDTO]) -> dict:
        """
        Extracts the rb number (experiment ID) and the experiment's part and puts them
        into a dictionary to get start and end dates for each one.

        Example output: {19510004: [1], 20310000: [1, 2, 3]}
        """

        exp_parts = {}

        for exp in experiments:
            exp_parts.setdefault(int(exp.rbNumber), []).append(exp.part)
        
        return exp_parts
    
    def get_experiments_from_scheduler(self, start_date, end_date) -> None:
        """
        Get experiments from the scheduler (including start and end dates of each part)
        and store a list of experiments in a model, ready to go into MongoDB

        Only 4 entire experiments are called from the scheduler (2 seconds apart from
        each other) to avoid the scheduler returning an error
        """

        experiments_data = self.scheduler_client.service.getExperimentDatesForInstrument(
            self.session_id,
            Config.config.experiments.instrument_name,
            {"startDate": "2019-01-01T00:00:00Z", "endDate": "2023-01-01T00:00:00Z"},
        )
        exp_parts = self.extract_experiment_part_numbers(experiments_data)

        req = 0
        for rb_number, parts in exp_parts.items():
            if req > 4:
                break

            experiment = self.scheduler_client.service.getExperiment(
                self.session_id,
                rb_number,
                "Gemini",
            )

            for part in experiment.experimentPartList:
                if part.partNumber in parts:
                    self.experiments.append(
                        ExperimentModel(
                            _id=f"{part.referenceNumber}-{part.partNumber}",
                            experiment_id=part.referenceNumber,
                            part=part.partNumber,
                            start_date=part.experimentStartDate,
                            end_date=part.experimentEndDate,
                        ),
                    )

            sleep(2)
            req += 1
            print(f"Requests sent: {req}")

        
        """
        Test code that I'm still not sure how it works

        test = self.scheduler_client.service.getExperiments(
            self.session_id,
            #{"key": 19510000, "value": "Gemini"}
            #{"key": [18325025, 19510000], "value": ["Gemini", "Gemini"]}
            {"18325025": "Gemini"}
            #{"key": "Gemini", "value": 19510000}
            #[18325025]
        )
        print(test)
        """

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

    @staticmethod
    async def get_experiments_from_database() -> List[dict]:
        """
        Get a list of experiments from the database, ordered by their ID.

        `_id` is the RB number and part number combined with a dash
        """

        experiments_query = MongoDBInterface.find(
            "experiments",
            sort=ParameterHandler.extract_order_data(["_id asc"]),
        )
        return await MongoDBInterface.query_to_list(experiments_query)
