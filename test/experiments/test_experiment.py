from datetime import datetime
from unittest.mock import patch

import pytest

from operationsgateway_api.src.exceptions import ExperimentDetailsError, ModelError
from operationsgateway_api.src.experiments.duplicate_part_selector import (
    DuplicatePartSelector,
)
from operationsgateway_api.src.experiments.experiment import Experiment
from operationsgateway_api.src.models import ExperimentPartMappingModel
from test.experiments.scheduler_mocking.experiments_mocks import (
    get_expected_experiment_models,
    get_experiments_mock,
)
from test.experiments.scheduler_mocking.get_exp_dates_mocks import (
    general_mock,
    missing_rb_number,
)


class TestExperiment:
    # Variables that are used for mocking
    config_instrument_names = ["Test Instrument", "Test Instrument #2"]
    config_scheduler_contact_date = datetime(2023, 3, 2, 10, 0)
    experiment_search_start_date = "2020-01-01T00:00:00Z"
    experiment_search_end_date = "2020-05-01T00:00:00Z"

    @patch(
        "operationsgateway_api.src.experiments.scheduler_interface.SchedulerInterface"
        ".__init__",
        return_value=None,
    )
    @patch(
        "operationsgateway_api.src.experiments.experiment.Experiment"
        "._get_collection_updated_date",
        return_value=datetime(2023, 3, 1, 10, 0),
    )
    @patch(
        "operationsgateway_api.src.config.Config.config.experiments"
        ".first_scheduler_contact_start_date",
        config_scheduler_contact_date,
    )
    @patch(
        "operationsgateway_api.src.experiments.background_scheduler_runner"
        ".BackgroundSchedulerRunner.get_next_run_task_date",
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
        "operationsgateway_api.src.config.Config.config.experiments.instrument_names",
        config_instrument_names,
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
        parts = experiment._map_experiments_to_part_numbers(
            data,
            self.config_instrument_names[0],
        )
        assert parts == [
            ExperimentPartMappingModel(
                experiment_id=20310000,
                parts=[3, 2, 1],
                instrument_name=self.config_instrument_names[0],
            ),
            ExperimentPartMappingModel(
                experiment_id=20310001,
                parts=[1, 2, 3],
                instrument_name=self.config_instrument_names[0],
            ),
            ExperimentPartMappingModel(
                experiment_id=18325019,
                parts=[4],
                instrument_name=self.config_instrument_names[0],
            ),
            ExperimentPartMappingModel(
                experiment_id=20310002,
                parts=[1],
                instrument_name=self.config_instrument_names[0],
            ),
        ]

    @patch(
        "operationsgateway_api.src.experiments.scheduler_interface.SchedulerInterface"
        ".__init__",
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
            experiment._map_experiments_to_part_numbers(
                data,
                self.config_instrument_names[0],
            )

    @patch(
        "operationsgateway_api.src.config.Config.config.experiments.instrument_names",
        config_instrument_names,
    )
    @patch(
        "operationsgateway_api.src.experiments.experiment.Experiment.__init__",
        return_value=None,
    )
    @pytest.mark.parametrize(
        "experiment_part_mappings, expected_pairs",
        [
            pytest.param(
                [
                    ExperimentPartMappingModel(
                        experiment_id=19510004,
                        parts=[1],
                        instrument_name=config_instrument_names[0],
                    ),
                    ExperimentPartMappingModel(
                        experiment_id=20310000,
                        parts=[1, 2, 3],
                        instrument_name=config_instrument_names[0],
                    ),
                ],
                [
                    {"key": 19510004, "value": config_instrument_names[0]},
                    {"key": 20310000, "value": config_instrument_names[0]},
                ],
                id="Simple use case",
            ),
            pytest.param(
                [
                    ExperimentPartMappingModel(
                        experiment_id=19510005,
                        parts=[1, 2, 3, 4, 5],
                        instrument_name=config_instrument_names[0],
                    ),
                ],
                [{"key": 19510005, "value": config_instrument_names[0]}],
                id="Single experiment",
            ),
            pytest.param(
                [
                    ExperimentPartMappingModel(
                        experiment_id=19510004,
                        parts=[1],
                        instrument_name=config_instrument_names[0],
                    ),
                    ExperimentPartMappingModel(
                        experiment_id=20310000,
                        parts=[1, 2, 3],
                        instrument_name=config_instrument_names[0],
                    ),
                    ExperimentPartMappingModel(
                        experiment_id=20310001,
                        parts=[1, 2, 3, 4],
                        instrument_name=config_instrument_names[0],
                    ),
                    ExperimentPartMappingModel(
                        experiment_id=20310002,
                        parts=[2, 3, 4, 5, 6],
                        instrument_name=config_instrument_names[1],
                    ),
                    ExperimentPartMappingModel(
                        experiment_id=20310003,
                        parts=[1, 2],
                        instrument_name=config_instrument_names[1],
                    ),
                ],
                [
                    {"key": 19510004, "value": config_instrument_names[0]},
                    {"key": 20310000, "value": config_instrument_names[0]},
                    {"key": 20310001, "value": config_instrument_names[0]},
                    {"key": 20310002, "value": config_instrument_names[1]},
                    {"key": 20310003, "value": config_instrument_names[1]},
                ],
                id="Multiple experiments",
            ),
            pytest.param(
                [
                    ExperimentPartMappingModel(
                        experiment_id=19510004,
                        parts=[1],
                        instrument_name=config_instrument_names[0],
                    ),
                    ExperimentPartMappingModel(
                        experiment_id=19510004,
                        parts=[1],
                        instrument_name=config_instrument_names[0],
                    ),
                ],
                [{"key": 19510004, "value": config_instrument_names[0]}],
                id="Duplicate experiments on input",
            ),
        ],
    )
    def test_generate_id_instrument_pairs(
        self,
        _,
        experiment_part_mappings,
        expected_pairs,
    ):
        experiment = Experiment()
        test_pairs = experiment._generate_id_instrument_name_pairs(
            experiment_part_mappings,
        )
        assert len(test_pairs) == len(expected_pairs)
        assert test_pairs == expected_pairs

    @patch(
        "operationsgateway_api.src.experiments.experiment.Experiment"
        "._generate_id_instrument_name_pairs",
        return_value=[
            {"key": 20310000, "value": config_instrument_names[0]},
            {"key": 20310001, "value": config_instrument_names[0]},
            {"key": 18325019, "value": config_instrument_names[1]},
            {"key": 20310002, "value": config_instrument_names[1]},
        ],
    )
    @patch(
        "operationsgateway_api.src.experiments.scheduler_interface.SchedulerInterface"
        ".__init__",
        return_value=None,
    )
    @pytest.mark.parametrize(
        "part_mappings, mock_selection, return_duplicate_parts",
        [
            pytest.param(
                [
                    ExperimentPartMappingModel(
                        experiment_id=20310000,
                        parts=[3, 2, 1],
                        instrument_name=config_instrument_names[0],
                    ),
                    ExperimentPartMappingModel(
                        experiment_id=20310001,
                        parts=[1, 2, 3],
                        instrument_name=config_instrument_names[0],
                    ),
                    ExperimentPartMappingModel(
                        experiment_id=18325019,
                        parts=[4],
                        instrument_name=config_instrument_names[1],
                    ),
                    ExperimentPartMappingModel(
                        experiment_id=20310002,
                        parts=[1],
                        instrument_name=config_instrument_names[1],
                    ),
                ],
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
                [
                    ExperimentPartMappingModel(
                        experiment_id=20310000,
                        parts=[1, 2],
                        instrument_name=config_instrument_names[0],
                    ),
                    ExperimentPartMappingModel(
                        experiment_id=18325019,
                        parts=[3, 4, 5],
                        instrument_name=config_instrument_names[1],
                    ),
                ],
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
        part_mappings,
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
                part_mappings,
            )
            experiments = experiment.scheduler.get_experiments(scheduler_input)
            experiment._extract_experiment_data(experiments, part_mappings)

            expected_experiments = get_expected_experiment_models(mock_selection)
            assert len(experiment.experiments) == len(expected_experiments)
            assert experiment.experiments == expected_experiments

    @patch(
        "operationsgateway_api.src.experiments.scheduler_interface.SchedulerInterface"
        ".__init__",
        return_value=None,
    )
    def test_valid_non_selected_extract_experiment_data(self, _):
        test_experiment = Experiment()
        experiment_mocks = get_experiments_mock(
            {18325019: [1, 2, 3, 4, 5]},
            return_duplicate_parts=False,
        )
        selected_parts = [4, 5]

        experiment_mappings = [
            ExperimentPartMappingModel(
                experiment_id=18325019,
                parts=selected_parts,
                instrument_name="Gemini",
            ),
        ]

        test_experiment._extract_experiment_data(experiment_mocks, experiment_mappings)
        expected_experiments = get_expected_experiment_models(
            {18325019: selected_parts},
        )

        assert len(test_experiment.experiments) == len(expected_experiments)
        assert test_experiment.experiments == expected_experiments

    @patch(
        "operationsgateway_api.src.experiments.experiment.Experiment"
        "._generate_id_instrument_name_pairs",
        return_value=[
            {"key": 20310000, "value": config_instrument_names[0]},
        ],
    )
    @patch(
        "operationsgateway_api.src.experiments.scheduler_interface.SchedulerInterface"
        ".__init__",
        return_value=None,
    )
    @pytest.mark.parametrize(
        "expected_exception, part_mappings, mock_selection",
        [
            pytest.param(
                ExperimentDetailsError,
                [
                    ExperimentPartMappingModel(
                        experiment_id=20310000,
                        parts=[1, 2],
                        instrument_name=config_instrument_names[0],
                    ),
                ],
                {20310000: [3]},
                id="AttributeError caught",
            ),
            pytest.param(
                ModelError,
                [
                    ExperimentPartMappingModel(
                        experiment_id=20310000,
                        parts=[1, 2],
                        instrument_name=config_instrument_names[0],
                    ),
                ],
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
        part_mappings,
        mock_selection,
    ):
        with patch(
            "operationsgateway_api.src.experiments.scheduler_interface"
            ".SchedulerInterface.get_experiments",
            return_value=get_experiments_mock(mock_selection, False),
        ):
            experiment = Experiment()
            scheduler_input = experiment._generate_id_instrument_name_pairs(
                part_mappings,
            )
            experiments = experiment.scheduler.get_experiments(scheduler_input)

            if expected_exception == ExperimentDetailsError:
                del experiments[0].experimentPartList[0].referenceNumber
            elif expected_exception == ModelError:
                experiments[0].experimentPartList[0].experimentStartDate = "Test"

            with pytest.raises(expected_exception):
                experiment._extract_experiment_data(experiments, part_mappings)

    @patch(
        "operationsgateway_api.src.experiments.scheduler_interface.SchedulerInterface"
        ".__init__",
        return_value=None,
    )
    @pytest.mark.parametrize(
        "experiment_id, mapping_models, expected_mapping",
        [
            pytest.param(
                20310001,
                [
                    ExperimentPartMappingModel(
                        experiment_id=20310001,
                        parts=[1, 2, 3],
                        instrument_name=config_instrument_names[0],
                    ),
                ],
                ExperimentPartMappingModel(
                    experiment_id=20310001,
                    parts=[1, 2, 3],
                    instrument_name=config_instrument_names[0],
                ),
                id="Single part list",
            ),
            pytest.param(
                20310000,
                [
                    ExperimentPartMappingModel(
                        experiment_id=20310000,
                        parts=[3, 2, 1],
                        instrument_name=config_instrument_names[1],
                    ),
                    ExperimentPartMappingModel(
                        experiment_id=20310001,
                        parts=[1, 2, 3],
                        instrument_name=config_instrument_names[0],
                    ),
                    ExperimentPartMappingModel(
                        experiment_id=18325019,
                        parts=[4],
                        instrument_name=config_instrument_names[0],
                    ),
                ],
                ExperimentPartMappingModel(
                    experiment_id=20310000,
                    parts=[3, 2, 1],
                    instrument_name=config_instrument_names[1],
                ),
                id="Multi-part list",
            ),
        ],
    )
    def test_valid_get_mapping_model_by_experiment_id(
        self,
        _,
        experiment_id,
        mapping_models,
        expected_mapping,
    ):
        test_experiment = Experiment()
        mapping = test_experiment._get_mapping_model_by_experiment_id(
            experiment_id,
            mapping_models,
        )
        assert mapping == expected_mapping

    @patch(
        "operationsgateway_api.src.experiments.scheduler_interface.SchedulerInterface"
        ".__init__",
        return_value=None,
    )
    def test_invalid_get_mapping_model_by_experiment_id(self, _):
        test_experiment = Experiment()

        with pytest.raises(ExperimentDetailsError):
            test_experiment._get_mapping_model_by_experiment_id(
                404,
                [
                    ExperimentPartMappingModel(
                        experiment_id=505,
                        parts=[1],
                        instrument_name=self.config_instrument_names[0],
                    ),
                ],
            )

    @patch(
        "operationsgateway_api.src.experiments.scheduler_interface.SchedulerInterface"
        ".__init__",
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
        "operationsgateway_api.src.experiments.scheduler_interface.SchedulerInterface"
        ".__init__",
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
