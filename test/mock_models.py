from typing import Any, Dict, Optional

from pydantic import BaseModel


class MockDeleteResult(BaseModel):
    acknowledged: bool
    deleted_count: int
    # Not needed for mocking tests
    raw_result: Optional[Dict[str, Any]] = None


class MockInsertOneResult(BaseModel):
    acknowledged: bool
    inserted_id: Any = None


class MockUpdateResult(BaseModel):
    acknowledged: bool
    matched_count: int
    modified_count: int
    # Not needed for mocking tests
    raw_result: Optional[Dict[str, Any]] = None
    upserted_id: Optional[Any] = None
