from datetime import datetime
import logging

from fastapi import APIRouter

from operationsgateway_api.src.experiments.experiment import Experiment

log = logging.getLogger()
router = APIRouter()


# TODO - add auth to this endpoint
@router.post(
    "/experiments",
    summary="Submit experiments from the scheduler to MongoDB",
    response_description="List of experiment IDs",
    tags=["Experiments"],
)
async def store_experiments_from_scheduler(
    start_date: datetime = None,
    end_date: datetime = None,
):

    # TODO - dates need to be in correct format: 2023-01-01T00:00:00Z
    # TODO - should the dates just be in config?
    # str(start_date) gets you 2023-01-01 00:00:00+00:00, causing unmarshalling error

    experiment = Experiment()
    await experiment.get_experiments_from_scheduler()
    await experiment.store_experiments()

    return [e.id_ for e in experiment.experiments]


@router.get(
    "/experiments",
    summary="Get experiments stored in database",
    response_description="List of experiments",
    tags=["Experiments"],
)
async def get_experiments():
    return await Experiment.get_experiments_from_database()
