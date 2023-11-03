from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class ExperimentDateDTO(BaseModel):
    instrument: str
    part: int
    rbNumber: Optional[str] = None
    scheduledDate: datetime
    timeAllocated: float


class ExperimentPartDTO(BaseModel):
    experimentEndDate: datetime
    experimentStartDate: datetime
    partNumber: Optional[int] = None
    referenceNumber: str
    status: str


class ExperimentDTO(BaseModel):
    experimentPartList: List[ExperimentPartDTO]
