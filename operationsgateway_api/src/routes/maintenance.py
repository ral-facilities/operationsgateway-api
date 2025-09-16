import json
import logging

from fastapi import APIRouter, Depends
from typing_extensions import Annotated

from operationsgateway_api.src.auth.authorisation import authorise_route
from operationsgateway_api.src.config import Config
from operationsgateway_api.src.models import MaintenanceModel, ScheduledMaintenanceModel


log = logging.getLogger()
router = APIRouter()
AuthoriseRoute = Annotated[str, Depends(authorise_route)]


@router.get(
    "/maintenance",
    summary="Get the current maintenance message and whether to show it",
    response_description="The current maintenance message and whether to show it",
    tags=["Maintenance"],
)
def get_maintenance() -> MaintenanceModel:
    return _get_maintenance()


@router.put(
    "/maintenance",
    summary="Set the current maintenance message and whether to show it",
    tags=["Maintenance"],
)
def set_maintenance(
    access_token: AuthoriseRoute,
    maintenance_body: MaintenanceModel,
) -> None:
    with open(Config.config.app.maintenance_file, "w") as f:
        f.write(maintenance_body.model_dump_json())


@router.get(
    "/scheduled_maintenance",
    summary="Get the current scheduled maintenance message and whether to show it",
    response_description=(
        "The current scheduled maintenance message and whether to show it"
    ),
    tags=["Maintenance"],
)
def get_scheduled_maintenance() -> ScheduledMaintenanceModel:
    return _get_scheduled_maintenance()


@router.put(
    "/scheduled_maintenance",
    summary="Set the current scheduled maintenance message and whether to show it",
    tags=["Maintenance"],
)
def set_scheduled_maintenance(
    access_token: AuthoriseRoute,
    maintenance_body: ScheduledMaintenanceModel,
) -> None:
    with open(Config.config.app.scheduled_maintenance_file, "w") as f:
        f.write(maintenance_body.model_dump_json())


def _get_maintenance() -> dict:
    with open(Config.config.app.maintenance_file, "rb") as f:
        return json.load(f)


def _get_scheduled_maintenance() -> dict:
    with open(Config.config.app.scheduled_maintenance_file, "rb") as f:
        return json.load(f)
