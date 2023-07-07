from typing import Any, Dict, Optional

from pydantic import BaseModel


class MockDeleteResult(BaseModel):
    acknowledged: bool
    deleted_count: int
    # Not needed for mocking tests
    raw_result: Optional[Dict[str, Any]]


class MockInsertOneResult(BaseModel):
    acknowledged: bool
    inserted_id: Any


class MockUpdateResult(BaseModel):
    acknowledged: bool
    matched_count: int
    modified_count: int
    # Not needed for mocking tests
    raw_result: Optional[Dict[str, Any]]
    upserted_id: Optional[Any]
