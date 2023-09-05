from copy import deepcopy
from datetime import datetime
from typing import Dict, List

from operationsgateway_api.src.models import ExperimentModel
from test.experiments.scheduler_mocking.models import ExperimentDTO, ExperimentPartDTO


def get_experiments_mock(
    selection: Dict[int, List[int]],
    return_duplicate_parts: bool,
) -> List[ExperimentDTO]:
    """
    Function to search through the mock data and return what's needed for the test.
    `mock_data` contains lots of different test data for different test cases (e.g.
    there's some duplicate parts to test `DuplicatePartSelector`) so this is a way to
    not repeat data for multiple tests while being able to have a wide range of test
    data.

    An example `selection` input: `{20310000: [1, 2], 18325019: [4]}` - keys are
    experiment IDs and values are a list of parts
    If `return_duplicate_parts` is set to False and there are duplicates on the part
    that's being requested for the mock, the first of the duplicates will be returned
    """

    mock = []

    for experiment_id, requested_parts in selection.items():
        requested_parts = deepcopy(requested_parts)
        experiment = mock_data[experiment_id]["mock"]

        parts_to_use = []
        for experiment_part in experiment.experimentPartList:
            if experiment_part.partNumber in requested_parts:
                parts_to_use.append(experiment_part)
                if not return_duplicate_parts:
                    requested_parts.remove(experiment_part.partNumber)

        experiment_mock = ExperimentDTO(experimentPartList=parts_to_use)
        mock.append(experiment_mock)

    return mock


def get_expected_experiment_models(
    selection: Dict[int, List[int]],
) -> List[ExperimentModel]:
    expected = []

    for experiment_id, requested_parts in selection.items():
        requested_parts = deepcopy(requested_parts)
        experiment_models = mock_data[experiment_id]["expected"]

        for model in experiment_models:
            if model.part in requested_parts:
                expected.append(model)
                requested_parts.remove(model.part)

    return expected


mock_data = {
    20310000: {
        "mock": ExperimentDTO(
            experimentPartList=[
                ExperimentPartDTO(
                    experimentEndDate=datetime(2020, 2, 25, 18, 0),
                    experimentStartDate=datetime(2020, 2, 25, 10, 0),
                    partNumber=1,
                    referenceNumber="20310000",
                    status="Delivered",
                ),
                ExperimentPartDTO(
                    experimentEndDate=datetime(2020, 2, 26, 18, 0),
                    experimentStartDate=datetime(2020, 2, 26, 10, 0),
                    partNumber=2,
                    referenceNumber="20310000",
                    status="Delivered",
                ),
                ExperimentPartDTO(
                    experimentEndDate=datetime(2020, 3, 2, 18, 0),
                    experimentStartDate=datetime(2020, 3, 2, 10, 0),
                    partNumber=3,
                    referenceNumber="20310000",
                    status="Delivered",
                ),
            ],
        ),
        "expected": [
            ExperimentModel(
                _id=None,
                experiment_id=20310000,
                part=1,
                start_date=datetime(2020, 2, 25, 10, 0),
                end_date=datetime(2020, 2, 25, 18, 0),
            ),
            ExperimentModel(
                _id=None,
                experiment_id=20310000,
                part=2,
                start_date=datetime(2020, 2, 26, 10, 0),
                end_date=datetime(2020, 2, 26, 18, 0),
            ),
            ExperimentModel(
                _id=None,
                experiment_id=20310000,
                part=3,
                start_date=datetime(2020, 3, 2, 10, 0),
                end_date=datetime(2020, 3, 2, 18, 0),
            ),
        ],
    },
    20310001: {
        "mock": ExperimentDTO(
            experimentPartList=[
                ExperimentPartDTO(
                    experimentEndDate=datetime(2020, 2, 24, 18, 0),
                    experimentStartDate=datetime(2020, 2, 24, 10, 0),
                    partNumber=1,
                    referenceNumber="20310001",
                    status="Delivered",
                ),
                ExperimentPartDTO(
                    experimentEndDate=datetime(2020, 2, 25, 18, 0),
                    experimentStartDate=datetime(2020, 2, 25, 10, 0),
                    partNumber=2,
                    referenceNumber="20310001",
                    status="Delivered",
                ),
                ExperimentPartDTO(
                    experimentEndDate=datetime(2020, 2, 26, 18, 0),
                    experimentStartDate=datetime(2020, 2, 26, 10, 0),
                    partNumber=3,
                    referenceNumber="20310001",
                    status="Delivered",
                ),
            ],
        ),
        "expected": [
            ExperimentModel(
                _id=None,
                experiment_id=20310001,
                part=1,
                start_date=datetime(2020, 2, 24, 10, 0),
                end_date=datetime(2020, 2, 24, 18, 0),
            ),
            ExperimentModel(
                _id=None,
                experiment_id=20310001,
                part=2,
                start_date=datetime(2020, 2, 25, 10, 0),
                end_date=datetime(2020, 2, 25, 18, 0),
            ),
            ExperimentModel(
                _id=None,
                experiment_id=20310001,
                part=3,
                start_date=datetime(2020, 2, 26, 10, 0),
                end_date=datetime(2020, 2, 26, 18, 0),
            ),
        ],
    },
    20310002: {
        "mock": ExperimentDTO(
            experimentPartList=[
                ExperimentPartDTO(
                    experimentEndDate=datetime(2020, 4, 30, 18, 0),
                    experimentStartDate=datetime(2020, 4, 30, 10, 0),
                    partNumber=1,
                    referenceNumber="20310002",
                    status="Delivered",
                ),
            ],
        ),
        "expected": [
            ExperimentModel(
                _id=None,
                experiment_id=20310002,
                part=1,
                start_date=datetime(2020, 4, 30, 10, 0),
                end_date=datetime(2020, 4, 30, 18, 0),
            ),
        ],
    },
    18325019: {
        "mock": ExperimentDTO(
            experimentPartList=[
                ExperimentPartDTO(
                    experimentEndDate=datetime(2018, 11, 23, 18, 0),
                    experimentStartDate=datetime(2018, 11, 23, 10, 0),
                    partNumber=1,
                    referenceNumber="18325019",
                    status="Changed",
                ),
                ExperimentPartDTO(
                    experimentEndDate=datetime(2018, 12, 1, 18, 0),
                    experimentStartDate=datetime(2018, 11, 30, 10, 0),
                    partNumber=2,
                    referenceNumber="18325019",
                    status="Published",
                ),
                ExperimentPartDTO(
                    experimentEndDate=datetime(2018, 12, 1, 18, 0),
                    experimentStartDate=datetime(2018, 11, 29, 10, 0),
                    partNumber=3,
                    referenceNumber="18325019",
                    status="Published",
                ),
                ExperimentPartDTO(
                    experimentEndDate=datetime(2020, 1, 6, 18, 0),
                    experimentStartDate=datetime(2020, 1, 3, 10, 0),
                    partNumber=4,
                    referenceNumber="18325019",
                    status="Published",
                ),
                ExperimentPartDTO(
                    experimentEndDate=datetime(2019, 6, 12, 18, 0),
                    experimentStartDate=datetime(2019, 6, 12, 10, 0),
                    partNumber=5,
                    referenceNumber="18325019",
                    status="Published",
                ),
                ExperimentPartDTO(
                    experimentEndDate=datetime(2019, 6, 12, 18, 0),
                    experimentStartDate=datetime(2019, 6, 12, 10, 0),
                    partNumber=5,
                    referenceNumber="18325019",
                    status="Changed",
                ),
            ],
        ),
        "expected": [
            ExperimentModel(
                _id=None,
                experiment_id=18325019,
                part=1,
                start_date=datetime(2018, 11, 23, 10, 0),
                end_date=datetime(2018, 11, 23, 18, 0),
            ),
            ExperimentModel(
                _id=None,
                experiment_id=18325019,
                part=2,
                start_date=datetime(2018, 11, 30, 10, 0),
                end_date=datetime(2018, 12, 1, 18, 0),
            ),
            ExperimentModel(
                _id=None,
                experiment_id=18325019,
                part=3,
                start_date=datetime(2018, 11, 29, 10, 0),
                end_date=datetime(2018, 12, 1, 18, 0),
            ),
            ExperimentModel(
                _id=None,
                experiment_id=18325019,
                part=4,
                start_date=datetime(2020, 1, 3, 10, 0),
                end_date=datetime(2020, 1, 6, 18, 0),
            ),
            ExperimentModel(
                _id=None,
                experiment_id=18325019,
                part=5,
                start_date=datetime(2019, 6, 12, 10, 0),
                end_date=datetime(2019, 6, 12, 18, 0),
            ),
        ],
    },
    # Used to test duplicate part selector
    12345678: {
        "mock": ExperimentDTO(
            experimentPartList=[
                ExperimentPartDTO(
                    experimentEndDate=datetime(2020, 4, 30, 18, 0),
                    experimentStartDate=datetime(2020, 4, 30, 10, 0),
                    partNumber=1,
                    referenceNumber="12345678",
                    status="Published",
                ),
                ExperimentPartDTO(
                    experimentEndDate=datetime(2020, 4, 30, 18, 0),
                    experimentStartDate=datetime(2020, 4, 30, 10, 0),
                    partNumber=1,
                    referenceNumber="12345678",
                    status="Delivered",
                ),
                ExperimentPartDTO(
                    experimentEndDate=datetime(2020, 4, 30, 18, 0),
                    experimentStartDate=datetime(2020, 4, 30, 10, 0),
                    partNumber=1,
                    referenceNumber="12345678",
                    status="Republished",
                ),
                ExperimentPartDTO(
                    experimentEndDate=datetime(2020, 4, 30, 18, 0),
                    experimentStartDate=datetime(2020, 4, 30, 10, 0),
                    partNumber=1,
                    referenceNumber="12345678",
                    status="Changed",
                ),
                ExperimentPartDTO(
                    experimentEndDate=datetime(2020, 5, 1, 18, 0),
                    experimentStartDate=datetime(2020, 5, 1, 10, 0),
                    partNumber=2,
                    referenceNumber="12345678",
                    status="Changed",
                ),
                ExperimentPartDTO(
                    experimentEndDate=datetime(2020, 5, 1, 18, 0),
                    experimentStartDate=datetime(2020, 5, 1, 10, 0),
                    partNumber=2,
                    referenceNumber="12345678",
                    status="Delivered",
                ),
                ExperimentPartDTO(
                    experimentEndDate=datetime(2020, 5, 2, 18, 0),
                    experimentStartDate=datetime(2020, 5, 2, 10, 0),
                    partNumber=3,
                    referenceNumber="12345678",
                    status="PublishRequested",
                ),
                ExperimentPartDTO(
                    experimentEndDate=datetime(2020, 5, 2, 18, 0),
                    experimentStartDate=datetime(2020, 5, 2, 10, 0),
                    partNumber=3,
                    referenceNumber="12345678",
                    status="RepublishRequested",
                ),
                ExperimentPartDTO(
                    experimentEndDate=datetime(2020, 5, 2, 18, 0),
                    experimentStartDate=datetime(2020, 5, 2, 10, 0),
                    partNumber=3,
                    referenceNumber="12345678",
                    status="Tentative",
                ),
                ExperimentPartDTO(
                    experimentEndDate=datetime(2020, 5, 2, 18, 0),
                    experimentStartDate=datetime(2020, 5, 2, 10, 0),
                    partNumber=3,
                    referenceNumber="12345678",
                    status="Postponed",
                ),
                ExperimentPartDTO(
                    experimentEndDate=datetime(2020, 5, 2, 18, 0),
                    experimentStartDate=datetime(2020, 5, 2, 10, 0),
                    partNumber=3,
                    referenceNumber="12345678",
                    status="Cancelled",
                ),
                ExperimentPartDTO(
                    experimentEndDate=datetime(2020, 5, 3, 18, 0),
                    experimentStartDate=datetime(2020, 5, 3, 10, 0),
                    partNumber=4,
                    referenceNumber="12345678",
                    status="Republished",
                ),
                ExperimentPartDTO(
                    experimentEndDate=datetime(2020, 5, 3, 18, 0),
                    experimentStartDate=datetime(2020, 5, 3, 10, 0),
                    partNumber=4,
                    referenceNumber="12345678",
                    status="Postponed",
                ),
            ],
        ),
        "expected": [
            ExperimentModel(
                _id=None,
                experiment_id=12345678,
                part=1,
                start_date=datetime(2020, 4, 30, 10, 0),
                end_date=datetime(2020, 4, 30, 18, 0),
            ),
            ExperimentModel(
                _id=None,
                experiment_id=12345678,
                part=2,
                start_date=datetime(2020, 5, 1, 10, 0),
                end_date=datetime(2020, 5, 1, 18, 0),
            ),
            ExperimentModel(
                _id=None,
                experiment_id=12345678,
                part=4,
                start_date=datetime(2020, 5, 3, 10, 0),
                end_date=datetime(2020, 5, 3, 18, 0),
            ),
        ],
    },
}
