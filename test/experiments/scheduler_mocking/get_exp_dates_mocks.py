from datetime import datetime

from test.experiments.scheduler_mocking.models import ExperimentDateDTO

general_mock = [
    ExperimentDateDTO(
        instrument="Gemini",
        part=3,
        rbNumber="20310000",
        scheduledDate=datetime(2020, 3, 2, 10, 0),
        timeAllocated=0.33333334,
    ),
    ExperimentDateDTO(
        instrument="Gemini",
        part=2,
        rbNumber="20310000",
        scheduledDate=datetime(2020, 2, 26, 10, 0),
        timeAllocated=0.33333334,
    ),
    ExperimentDateDTO(
        instrument="Gemini",
        part=1,
        rbNumber="20310000",
        scheduledDate=datetime(
            2020,
            2,
            25,
            10,
            0,
        ),
        timeAllocated=0.33333334,
    ),
    ExperimentDateDTO(
        instrument="Gemini",
        part=1,
        rbNumber="20310001",
        scheduledDate=datetime(2020, 2, 24, 10, 0),
        timeAllocated=0.33333334,
    ),
    ExperimentDateDTO(
        instrument="Gemini",
        part=2,
        rbNumber="20310001",
        scheduledDate=datetime(2020, 2, 25, 10, 0),
        timeAllocated=0.33333334,
    ),
    ExperimentDateDTO(
        instrument="Gemini",
        part=3,
        rbNumber="20310001",
        scheduledDate=datetime(2020, 2, 26, 10, 0),
        timeAllocated=0.33333334,
    ),
    ExperimentDateDTO(
        instrument="Gemini",
        part=4,
        rbNumber="18325019",
        scheduledDate=datetime(2020, 1, 3, 10, 0),
        timeAllocated=0.6666667,
    ),
    ExperimentDateDTO(
        instrument="Gemini",
        part=1,
        rbNumber="20310002",
        scheduledDate=datetime(2020, 4, 30, 10, 0),
        timeAllocated=0.33333334,
    ),
]

missing_rb_number = [
    ExperimentDateDTO(
        instrument="Gemini",
        part=1,
        scheduledDate=datetime(2020, 4, 30, 10, 0),
        timeAllocated=0.33333334,
    ),
]
# rbNumber needs to be completely removed, not just set to `None`
del missing_rb_number[0].rbNumber
