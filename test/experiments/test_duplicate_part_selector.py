from datetime import datetime

import pytest

from operationsgateway_api.src.exceptions import ExperimentDetailsError
from operationsgateway_api.src.experiments.duplicate_part_selector import (
    DuplicatePartSelector,
    PartStatus,
)
from test.experiments.scheduler_mocking.experiments_mocks import get_experiments_mock
from test.experiments.scheduler_mocking.models import ExperimentPartDTO


class TestDuplicatePartSelector:
    @pytest.mark.parametrize(
        "mock_selection, expected_part",
        [
            pytest.param(
                {12345678: [1]},
                ExperimentPartDTO(
                    experimentEndDate=datetime(2020, 4, 30, 18, 0),
                    experimentStartDate=datetime(2020, 4, 30, 10, 0),
                    partNumber=1,
                    referenceNumber="12345678",
                    status="Delivered",
                ),
                id="Selection from valid part statuses",
            ),
            pytest.param(
                {12345678: [4]},
                ExperimentPartDTO(
                    experimentEndDate=datetime(2020, 5, 3, 18, 0),
                    experimentStartDate=datetime(2020, 5, 3, 10, 0),
                    partNumber=4,
                    referenceNumber="12345678",
                    status="Republished",
                ),
                id="Selection from valid and invalid part statuses",
            ),
        ],
    )
    def test_select_part(self, mock_selection, expected_part):
        experiment = get_experiments_mock(mock_selection, return_duplicate_parts=True)
        part_selector = DuplicatePartSelector(
            experiment[0].experimentPartList[0].partNumber,
            experiment[0].experimentPartList,
        )

        selected_part = part_selector.select_part()
        assert selected_part == expected_part

    @pytest.mark.parametrize(
        "mock_selection",
        [
            pytest.param(
                {12345678: [3]},
                id="Part with all invalid statuses",
            ),
        ],
    )
    def test_invalid_part_status(self, mock_selection):
        experiment = get_experiments_mock(mock_selection, return_duplicate_parts=True)
        part_selector = DuplicatePartSelector(
            experiment[0].experimentPartList[0].partNumber,
            experiment[0].experimentPartList,
        )

        with pytest.raises(ExperimentDetailsError):
            part_selector.select_part()

    @pytest.mark.parametrize(
        "mock_selection, expected_parts",
        [
            pytest.param(
                {12345678: [2]},
                [
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
                ],
                id="Part with valid statuses",
            ),
            pytest.param(
                {12345678: [3]},
                [],
                id="Part with all invalid statuses",
            ),
            pytest.param(
                {12345678: [4]},
                [
                    ExperimentPartDTO(
                        experimentEndDate=datetime(2020, 5, 3, 18, 0),
                        experimentStartDate=datetime(2020, 5, 3, 10, 0),
                        partNumber=4,
                        referenceNumber="12345678",
                        status="Republished",
                    ),
                ],
                id="Part with mixture of valid and invalid statuses",
            ),
        ],
    )
    def test_remove_parts(self, mock_selection, expected_parts):
        experiment = get_experiments_mock(mock_selection, return_duplicate_parts=True)
        part_selector = DuplicatePartSelector(
            experiment[0].experimentPartList[0].partNumber,
            experiment[0].experimentPartList,
        )
        part_selector._remove_parts()

        assert part_selector.parts == expected_parts

    @pytest.mark.parametrize(
        "mock_selection, expected_parts",
        [
            pytest.param(
                {12345678: [1]},
                [
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
                        status="Published",
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
                ],
                id="Valid statuses only",
            ),
            pytest.param(
                {12345678: [4]},
                [
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
                id="Mixture of valid and invalid statuses (inputted in correct order)",
            ),
        ],
    )
    def test_order_parts_by_status(self, mock_selection, expected_parts):
        experiment = get_experiments_mock(mock_selection, return_duplicate_parts=True)
        part_selector = DuplicatePartSelector(
            experiment[0].experimentPartList[0].partNumber,
            experiment[0].experimentPartList,
        )
        part_selector._order_parts_by_status()

        assert part_selector.parts == expected_parts

    @pytest.mark.parametrize(
        "mock_selection, expected_precedence",
        [
            pytest.param(
                {12345678: [1]},
                PartStatus.PUBLISHED,
                id="Published",
            ),
            pytest.param(
                {12345678: [2]},
                PartStatus.CHANGED,
                id="Changed",
            ),
            pytest.param(
                {12345678: [3]},
                PartStatus.PUBLISHREQUESTED,
                id="PublishRequested",
            ),
            pytest.param(
                {12345678: [4]},
                PartStatus.REPUBLISHED,
                id="Republished",
            ),
        ],
    )
    def test_get_status_precedence(self, mock_selection, expected_precedence):
        experiment = get_experiments_mock(mock_selection, return_duplicate_parts=True)
        part_selector = DuplicatePartSelector(
            experiment[0].experimentPartList[0].partNumber,
            experiment[0].experimentPartList,
        )
        precedence = part_selector._get_status_precedence(part_selector.parts[0])

        assert precedence == expected_precedence
