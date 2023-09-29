from datetime import datetime
import logging
from typing import Any, Dict, List, Tuple, Union

from pydantic import ValidationError

from operationsgateway_api.src.config import Config
from operationsgateway_api.src.exceptions import ExperimentDetailsError, ModelError
from operationsgateway_api.src.experiments.duplicate_part_selector import (
    DuplicatePartSelector,
)
import operationsgateway_api.src.experiments.runners as runners
from operationsgateway_api.src.experiments.scheduler_interface import SchedulerInterface
from operationsgateway_api.src.models import ExperimentModel, ExperimentPartMappingModel
from operationsgateway_api.src.mongo.interface import MongoDBInterface
from operationsgateway_api.src.routes.common_parameters import ParameterHandler

log = logging.getLogger()


class Experiment:
    def __init__(self) -> None:
        self.scheduler = SchedulerInterface()
        self.experiments = []

    async def get_experiments_from_scheduler(self) -> None:
        """
        Get experiments from the Scheduler (including start and end dates of each part)
        and store a list of experiments in a model, ready to be stored in MongoDB.

        This is done by sending two calls to the Scheduler, one to get the experiment
        IDs (and part numbers) that meet the date range and the second to get the start
        and end dates for each experiment part.

        The start and end dates for the first call depend on when the MongoDB collection
        was last updated (or the appropriate config option if no data exists in the
        collection) and when the next scheduled task will be run
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

        experiment_part_mappings = []
        for instrument_name in Config.config.experiments.instrument_names:
            exp_data = self.scheduler.get_experiment_dates_for_instrument(
                instrument_name,
                experiment_search_start_date,
                experiment_search_end_date,
            )
            experiment_part_mappings.extend(
                self._map_experiments_to_part_numbers(exp_data, instrument_name),
            )

        ids_for_scheduler_call = self._generate_id_instrument_name_pairs(
            experiment_part_mappings,
        )
        experiments = self.scheduler.get_experiments(ids_for_scheduler_call)
        self._extract_experiment_data(experiments, experiment_part_mappings)

    async def store_experiments(self) -> List[str]:
        """
        Store the experiments into MongoDB, using `upsert` to insert any experiments
        that haven't yet been inserted into the database
        """

        inserted_ids = []
        for experiment in self.experiments:
            experiment_data = experiment.dict(
                by_alias=True,
                exclude_unset=True,
                exclude={"id_"},
            )

            update_result = await MongoDBInterface.update_one(
                "experiments",
                experiment_data,
                {"$set": experiment_data},
                upsert=True,
            )
            # This means the document was updated, not inserted. The _id needs to be
            # found to be used as a response
            if update_result.upserted_id is None:
                updated_experiment = await MongoDBInterface.find_one(
                    "experiments",
                    experiment_data,
                )

                log.debug(
                    "Experiment was updated, found experiment _id: %s",
                    str(updated_experiment["_id"]),
                )
                inserted_ids.append(f"Updated {str(updated_experiment['_id'])}")
            else:
                inserted_ids.append(str(update_result.upserted_id))

        await self._update_modification_time()

        return inserted_ids

    def _map_experiments_to_part_numbers(
        self,
        # List of zeep experimentDateDTO's
        experiments: List[Any],
        instrument_name: str,
    ) -> List[ExperimentPartMappingModel]:
        """
        Given a list of experiments retrieved from the Scheduler, extract RB numbers
        (experiment IDs) and the experiment's parts and return a list of experiment part
        mappings that contain this data and which instrument the experiment/its parts
        belong to
        """

        exp_parts = {}

        for exp in experiments:
            try:
                exp_parts.setdefault(int(exp.rbNumber), []).append(exp.part)
            except AttributeError as exc:
                raise ExperimentDetailsError(str(exc)) from exc

        log.debug("Experiment parts: %s", exp_parts)

        part_mappings = [
            ExperimentPartMappingModel(
                experiment_id=exp_id,
                parts=parts,
                instrument_name=instrument_name,
            )
            for exp_id, parts in exp_parts.items()
        ]

        return part_mappings

    def _generate_id_instrument_name_pairs(
        self,
        experiment_part_mappings: List[ExperimentPartMappingModel],
    ) -> List[Dict[str, Union[str, int]]]:
        """
        Generate a list of dictionaries in the format accepted by the Scheduler to get
        details of multiple experiments. If duplicate part mappings are passed, only one
        pair should be returned.
        """

        id_name_pairs = [
            {"key": mapping.experiment_id, "value": mapping.instrument_name}
            for mapping in experiment_part_mappings
        ]

        # Create a list of tuples (which are hashable) containing dictionary items,
        # store them in a set to remove duplicates and convert the remaining tuples back
        # into dictionaries, stored in a list
        duplicates_removed = [
            dict(t) for t in {tuple(d.items()) for d in id_name_pairs}
        ]
        # Testing revealed the above list comprehension doesn't guarantee the order of
        # the dictionaries so explict sorting is needed
        ordered_list = sorted(duplicates_removed, key=lambda d: d["key"])
        log.debug("Experiments to query for: %s", ordered_list)

        return ordered_list

    def _extract_experiment_data(
        self,
        experiments: list,
        experiment_part_mappings: List[ExperimentPartMappingModel],
    ) -> None:
        """
        Extract relevant attributes from experiment data that the Scheduler responded
        with and put them into a Pydantic model, so the data can be easily validation
        and stored in the database
        """

        for experiment in experiments:
            try:
                duplicate_selectors, non_duplicate_parts = self._detect_duplicate_parts(
                    experiment,
                )
                selected_parts = (
                    self._select_duplicate_parts(duplicate_selectors)
                    if duplicate_selectors
                    else []
                )
                # Combine selected duplicate parts with non duplicates and sort based on
                # experiment ID and part number
                experiment_parts = selected_parts + non_duplicate_parts
                experiment_parts.sort(
                    key=lambda part: (part.referenceNumber, part.partNumber),
                )

                for part in experiment_parts:
                    part_mapping = self._get_mapping_model_by_experiment_id(
                        int(part.referenceNumber),
                        experiment_part_mappings,
                    )

                    if part.partNumber in part_mapping.parts:
                        self.experiments.append(
                            ExperimentModel(
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

    def _get_mapping_model_by_experiment_id(
        self,
        experiment_id: int,
        mapping_models: List[ExperimentPartMappingModel],
    ):
        """
        Search through a list of experiment part mapping models and return the one with
        a matching experiment ID
        """

        for mapping in mapping_models:
            if mapping.experiment_id == experiment_id:
                return mapping

        log.error(
            "Part mapping for %s failed. Mapping to search through: %s",
            experiment_id,
            mapping_models,
        )
        raise ExperimentDetailsError(f"Lookup of part mapping {experiment_id} failed")

    def _detect_duplicate_parts(
        self,
        experiment,
    ) -> Tuple[List[DuplicatePartSelector], list]:
        """
        Detect which experiment parts are duplicated (i.e. multiple parts with the same
        part number). For each part number that's a duplicate, create
        `DuplicatePartSelector` so the part that should be used can be selected. Return
        a list of these along with the parts that aren't duplicates
        """

        parts = {}
        for part in experiment.experimentPartList:
            parts.setdefault(part.partNumber, []).append(part)

        duplicate_part_selectors = []
        non_duplicate_parts = []

        for part_number, part in parts.items():
            if len(part) > 1:
                duplicate_part_selectors.append(
                    DuplicatePartSelector(part_number, part),
                )
            elif len(part) == 1:
                non_duplicate_parts.append(part[0])

        return duplicate_part_selectors, non_duplicate_parts

    def _select_duplicate_parts(self, duplicate_selectors):
        return [selector.select_part() for selector in duplicate_selectors]

    async def _update_modification_time(self) -> None:
        """
        Update the modification time for the collection with the current datetime
        """

        await MongoDBInterface.update_one(
            "experiments",
            {"collection_last_updated": {"$exists": True}},
            {"$set": {"collection_last_updated": datetime.now()}},
            upsert=True,
        )

    async def _get_collection_updated_date(self) -> Union[datetime, None]:
        """
        Retrieve the datetime of when the collection was last updated
        """

        collection_update_date = await MongoDBInterface.find_one(
            "experiments",
            filter_={"collection_last_updated": {"$exists": True}},
        )

        if collection_update_date:
            return collection_update_date["collection_last_updated"]
        else:
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
