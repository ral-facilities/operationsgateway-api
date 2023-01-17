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
async def store_experiments_from_scheduler():
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
