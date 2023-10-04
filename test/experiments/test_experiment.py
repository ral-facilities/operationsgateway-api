from datetime import datetime
from unittest.mock import patch

import pytest

from operationsgateway_api.src.exceptions import ExperimentDetailsError, ModelError
from operationsgateway_api.src.experiments.duplicate_part_selector import (
    DuplicatePartSelector,
)
from operationsgateway_api.src.experiments.experiment import Experiment
from test.experiments.scheduler_mocking.experiments_mocks import (
    get_expected_experiment_models,
    get_experiments_mock,
)
from test.experiments.scheduler_mocking.get_exp_dates_mocks import (
    general_mock,
    missing_rb_number,
)
from test.sessions.mock_models import MockUpdateResult


class TestExperiment:
    # Variables that are used for mocking
    config_instrument_name = "Test Instrument"
    config_scheduler_contact_date = datetime(2023, 3, 2, 10, 0)
    experiment_search_start_date = "2020-01-01T00:00:00Z"
    experiment_search_end_date = "2020-05-01T00:00:00Z"

    @patch(
        "operationsgateway_api.src.experiments.scheduler_interface.SchedulerInterface.__init__",
        return_value=None,
    )
    @patch(
        "operationsgateway_api.src.experiments.experiment.Experiment._get_collection_updated_date",
        return_value=datetime(2023, 3, 1, 10, 0),
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.experiments"
        ".first_scheduler_contact_start_date",
        config_scheduler_contact_date,
    )
    @patch(
        "operationsgateway_api.src.experiments.background_scheduler_runner.BackgroundSchedulerRunner.get_next_run_task_date",
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
        return_value=get_experiments_mock(
            {20310001: [1, 2, 3], 18325019: [4], 20310002: [1]},
            return_duplicate_parts=True,
        ),
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.experiments.instrument_name",
        config_instrument_name,
    )
    @pytest.mark.asyncio
    async def test_get_experiments_from_scheduler(self, _, __, ___, ____, _____):
        test_experiment = Experiment()
        await test_experiment.get_experiments_from_scheduler()

        expected_experiments = get_expected_experiment_models(
            {20310001: [1, 2, 3], 18325019: [4], 20310002: [1]},
        )
        assert test_experiment.experiments == expected_experiments

    @patch(
        "operationsgateway_api.src.experiments.scheduler_interface.SchedulerInterface"
        ".__init__",
        return_value=None,
    )
    @pytest.mark.asyncio
    async def test_store_experiments(self, _):
        """
        This test covers `Experiment.store_experiments()` by mocking the storage of 5
        experiments. The third experiment is mocked to not have an upserted ID returned
        from the database (hence the `None` value in `upserted_ids`) which means the
        document was updated, not inserted. `store_experiments()` has some specific
        logic for this use case - it makes a query to the database to find the `_id` and
        adds it to a list of IDs which are returned by `store_experiments()`
        """

        test_experiment = Experiment()
        test_experiment.experiments = get_expected_experiment_models(
            {20310001: [1, 2, 3], 18325019: [4], 20310002: [1]},
        )

        upserted_ids = ["ObjectId 1", "ObjectId 2", None, "ObjectId 3", "ObjectId 4"]
        update_results = [
            MockUpdateResult(
                acknowledged=True,
                matched_count=1,
                modified_count=1,
                upserted_id=_id,
            )
            for _id in upserted_ids
        ]
        # For some reason, you need to have an additional element in the list in order
        # to prevent a StopAsyncIteration exception from being raised. It doesn't
        # actually get used in the test, hence `None` is used
        update_results.append(None)

        # The third experiment was inserted, not updated. We want to mock this query and
        # force `_id` tha we can assert against
        find_one_result = test_experiment.experiments[2].dict()
        find_one_result["_id"] = "Pre-existing ObjectId 1"

        expected_ids = [
            "ObjectId 1",
            "ObjectId 2",
            "Updated Pre-existing ObjectId 1",
            "ObjectId 3",
            "ObjectId 4",
        ]

        with patch(
            "operationsgateway_api.src.mongo.interface.MongoDBInterface.update_one",
            side_effect=update_results,
        ):
            with patch(
                "operationsgateway_api.src.mongo.interface.MongoDBInterface.find_one",
                return_value=find_one_result,
            ):
                inserted_ids = await test_experiment.store_experiments()
                assert inserted_ids == expected_ids

    @patch(
        "operationsgateway_api.src.experiments.scheduler_interface.SchedulerInterface.__init__",
        return_value=None,
    )
    @patch(
        "operationsgateway_api.src.experiments.scheduler_interface.SchedulerInterface"
        ".get_experiment_dates_for_instrument",
        return_value=general_mock,
    )
    def test_valid_map_experiment_part_numbers(self, _, __):
        experiment = Experiment()
        data = experiment.scheduler.get_experiment_dates_for_instrument(
            TestExperiment.experiment_search_start_date,
            TestExperiment.experiment_search_end_date,
        )
        parts = experiment._map_experiments_to_part_numbers(data)
        assert parts == {
            20310000: [3, 2, 1],
            20310001: [1, 2, 3],
            18325019: [4],
            20310002: [1],
        }

    @patch(
        "operationsgateway_api.src.experiments.scheduler_interface.SchedulerInterface.__init__",
        return_value=None,
    )
    @patch(
        "operationsgateway_api.src.experiments.scheduler_interface.SchedulerInterface"
        ".get_experiment_dates_for_instrument",
        return_value=missing_rb_number,
    )
    def test_invalid_map_experiment_part_numbers(self, _, __):
        experiment = Experiment()
        data = experiment.scheduler.get_experiment_dates_for_instrument(
            TestExperiment.experiment_search_start_date,
            TestExperiment.experiment_search_end_date,
        )

        with pytest.raises(ExperimentDetailsError):
            experiment._map_experiments_to_part_numbers(data)

    @patch(
        "operationsgateway_api.src.config.Config.config.experiments.instrument_name",
        config_instrument_name,
    )
    @patch(
        "operationsgateway_api.src.experiments.experiment.Experiment.__init__",
        return_value=None,
    )
    @pytest.mark.parametrize(
        "experiment_parts, expected_pairs",
        [
            pytest.param(
                {19510004: [1], 20310000: [1, 2, 3]},
                [
                    {"key": 19510004, "value": config_instrument_name},
                    {"key": 20310000, "value": config_instrument_name},
                ],
                id="Simple use case",
            ),
            pytest.param(
                {19510005: [1, 2, 4, 5]},
                [{"key": 19510005, "value": config_instrument_name}],
                id="Single experiment",
            ),
            pytest.param(
                {
                    19510004: [1],
                    20310000: [1, 2, 3],
                    20310001: [1, 2, 3, 4],
                    20310002: [2, 3, 4, 5, 6],
                    20310003: [1, 2],
                },
                [
                    {"key": 19510004, "value": config_instrument_name},
                    {"key": 20310000, "value": config_instrument_name},
                    {"key": 20310001, "value": config_instrument_name},
                    {"key": 20310002, "value": config_instrument_name},
                    {"key": 20310003, "value": config_instrument_name},
                ],
                id="Multiple experiments",
            ),
            pytest.param(
                {19510004: [1], 19510004: [1]},  # noqa: F601
                [{"key": 19510004, "value": config_instrument_name}],
                id="Duplicate experiments on input",
            ),
        ],
    )
    def test_generate_id_instrument_pairs(self, _, experiment_parts, expected_pairs):
        experiment = Experiment()
        test_pairs = experiment._generate_id_instrument_name_pairs(experiment_parts)
        assert test_pairs == expected_pairs

    @patch(
        "operationsgateway_api.src.experiments.experiment.Experiment._generate_id_instrument_name_pairs",
        return_value=[
            {"key": 20310000, "value": config_instrument_name},
            {"key": 20310001, "value": config_instrument_name},
            {"key": 18325019, "value": config_instrument_name},
            {"key": 20310002, "value": config_instrument_name},
        ],
    )
    @patch(
        "operationsgateway_api.src.experiments.scheduler_interface.SchedulerInterface.__init__",
        return_value=None,
    )
    @pytest.mark.parametrize(
        "parts_mapping, mock_selection, return_duplicate_parts",
        [
            pytest.param(
                {
                    20310000: [3, 2, 1],
                    20310001: [1, 2, 3],
                    18325019: [4],
                    20310002: [1],
                },
                {
                    20310000: [1, 2, 3],
                    20310001: [1, 2, 3],
                    20310002: [1],
                    18325019: [4],
                },
                False,
                id="Normal use case",
            ),
            pytest.param(
                {20310000: [1, 2], 18325019: [3, 4, 5]},
                {20310000: [1, 2], 18325019: [3, 4, 5]},
                True,
                id="Duplicate experiment parts",
            ),
        ],
    )
    def test_valid_extract_experiment_data(
        self,
        _,
        __,
        parts_mapping,
        mock_selection,
        return_duplicate_parts,
    ):
        with patch(
            "operationsgateway_api.src.experiments.scheduler_interface"
            ".SchedulerInterface.get_experiments",
            return_value=get_experiments_mock(mock_selection, return_duplicate_parts),
        ):
            experiment = Experiment()
            scheduler_input = experiment._generate_id_instrument_name_pairs(
                parts_mapping,
            )
            experiments = experiment.scheduler.get_experiments(scheduler_input)
            experiment._extract_experiment_data(experiments, parts_mapping)

            expected_experiments = get_expected_experiment_models(mock_selection)

            assert len(experiment.experiments) == len(expected_experiments)
            assert experiment.experiments == expected_experiments

    @patch(
        "operationsgateway_api.src.experiments.experiment.Experiment._generate_id_instrument_name_pairs",
        return_value=[
            {"key": 20310000, "value": config_instrument_name},
        ],
    )
    @patch(
        "operationsgateway_api.src.experiments.scheduler_interface.SchedulerInterface.__init__",
        return_value=None,
    )
    @pytest.mark.parametrize(
        "expected_exception, parts_mapping, mock_selection",
        [
            pytest.param(
                ExperimentDetailsError,
                {20310000: [3]},
                {20310000: [3]},
                id="AttributeError caught",
            ),
            pytest.param(
                ModelError,
                {20310000: [2]},
                {20310000: [2]},
                id="ValidationError (Pydantic) caught",
            ),
        ],
    )
    def test_invalid_extract_experiment_data(
        self,
        _,
        __,
        expected_exception,
        parts_mapping,
        mock_selection,
    ):
        with patch(
            "operationsgateway_api.src.experiments.scheduler_interface"
            ".SchedulerInterface.get_experiments",
            return_value=get_experiments_mock(mock_selection, False),
        ):

            experiment = Experiment()
            scheduler_input = experiment._generate_id_instrument_name_pairs(
                parts_mapping,
            )
            experiments = experiment.scheduler.get_experiments(scheduler_input)

            if expected_exception == ExperimentDetailsError:
                del experiments[0].experimentPartList[0].referenceNumber
            elif expected_exception == ModelError:
                experiments[0].experimentPartList[0].experimentStartDate = "Test"

            with pytest.raises(expected_exception):
                experiment._extract_experiment_data(experiments, parts_mapping)

    @patch(
        "operationsgateway_api.src.experiments.scheduler_interface.SchedulerInterface.__init__",
        return_value=None,
    )
    @pytest.mark.parametrize(
        "mock_selection, expected_duplicate_part_numbers"
        ", expected_non_duplicate_part_numbers",
        [
            # Non-duplicate parts only
            pytest.param(
                {20310000: [3]},
                [],
                [3],
                id="Single non-duplicate part",
            ),
            pytest.param(
                {20310001: [1, 2, 3]},
                [],
                [1, 2, 3],
                id="Multiple non-duplicate parts",
            ),
            # Duplicate parts only
            pytest.param({18325019: [5]}, [5], [], id="Single duplicate part"),
            pytest.param(
                {12345678: [1, 2]},
                [1, 2],
                [],
                id="Mutliple duplicate parts",
            ),
            # Mixture of duplicate and non-duplicate parts
            pytest.param(
                {18325019: [3, 5]},
                [5],
                [3],
                id="Single duplicate, single non-duplicate part",
            ),
            pytest.param(
                {18325019: [3, 4, 5]},
                [5],
                [3, 4],
                id="Single duplicate part, multiple non-duplicate parts",
            ),
        ],
    )
    def test_detect_duplicate_parts_mixture(
        self,
        _,
        mock_selection,
        expected_duplicate_part_numbers,
        expected_non_duplicate_part_numbers,
    ):
        test_experiment = get_experiments_mock(mock_selection, True)[0]

        expected_non_duplicates = []
        parts_grouped_by_part_number = {}
        for part in test_experiment.experimentPartList:
            parts_grouped_by_part_number.setdefault(part.partNumber, []).append(part)

        expected_duplicate_selectors = [
            DuplicatePartSelector(
                part_number,
                parts_grouped_by_part_number[part_number],
            )
            for part_number in expected_duplicate_part_numbers
        ]
        expected_non_duplicates = [
            parts_grouped_by_part_number[part_number][0]
            for part_number in expected_non_duplicate_part_numbers
        ]

        experiment = Experiment()
        duplicate_selectors, non_duplicate_parts = experiment._detect_duplicate_parts(
            test_experiment,
        )

        for test_selector, expected_selector in zip(
            duplicate_selectors,
            expected_duplicate_selectors,
        ):
            assert test_selector.part_number == expected_selector.part_number
            assert test_selector.parts == expected_selector.parts

        assert non_duplicate_parts == expected_non_duplicates

    @patch(
        "operationsgateway_api.src.experiments.scheduler_interface.SchedulerInterface.__init__",
        return_value=None,
    )
    @pytest.mark.parametrize(
        "mock_results_returned",
        [
            pytest.param(True, id="Mock results being returned"),
            pytest.param(False, id="Mock no results being returned"),
        ],
    )
    @pytest.mark.asyncio
    async def test_get_collection_updated_date(self, _, mock_results_returned):
        test_experiment = Experiment()

        mock_return_value = (
            {"collection_last_updated": datetime(2023, 3, 10, 10, 0)}
            if mock_results_returned
            else None
        )

        with patch(
            "operationsgateway_api.src.mongo.interface.MongoDBInterface.find_one",
            return_value=mock_return_value,
        ) as mock_database_query:
            collection_updated_date = (
                await test_experiment._get_collection_updated_date()
            )

            assert mock_database_query.call_count == 1

            if mock_results_returned:
                assert collection_updated_date == datetime(2023, 3, 10, 10, 0)
            else:
                assert collection_updated_date is None
