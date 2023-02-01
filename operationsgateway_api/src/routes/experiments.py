import logging

from fastapi import APIRouter, Depends

from operationsgateway_api.src.auth.authorisation import (
    authorise_route,
    authorise_token,
)
from operationsgateway_api.src.error_handling import endpoint_error_handling
from operationsgateway_api.src.experiments.experiment import Experiment

log = logging.getLogger()
router = APIRouter()


@router.post(
    "/experiments",
    summary="Submit experiments from the scheduler to MongoDB",
    response_description="List of experiment IDs",
    tags=["Experiments"],
)
@endpoint_error_handling
async def store_experiments_from_scheduler(
    access_token: str = Depends(authorise_route),  # noqa: B008
):
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
@endpoint_error_handling
async def get_experiments(
    access_token: str = Depends(authorise_token),  # noqa: B008
):
    return await Experiment.get_experiments_from_database()
