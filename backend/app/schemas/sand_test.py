from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel

class ValueEntry(BaseModel):
    parameter_id: int
    measured_value: float

class SandTestCreate(BaseModel):
    line_code: str
    test_type: str = "HOURLY_PHYSICAL"
    test_date: str  # YYYY-MM-DD
    shift: int  # 1, 2, 3
    test_hour: int  # 1..24
    batch_number: Optional[str] = None
    notes: Optional[str] = None
    values: list[ValueEntry]

class CorrectionRequestCreate(BaseModel):
    value_id: int
    requested_value: float
    reason: str

class SandTestValueResponse(BaseModel):
    id: int
    parameter_id: int
    parameter_name: Optional[str] = None
    parameter_code: Optional[str] = None
    measured_value: float
    unit: str
    status: str
    is_corrected: bool
    original_value: Optional[float] = None
    correction_reason: Optional[str] = None

    class Config:
        from_attributes = True

class SandTestRecordResponse(BaseModel):
    id: int
    test_number: str
    line_code: str
    test_type: str
    test_date: str
    shift: int
    test_hour: int
    timestamp: datetime
    batch_number: Optional[str] = None
    status: str
    notes: Optional[str] = None
    operator_name: Optional[str] = None
    values: list[SandTestValueResponse] = []

    class Config:
        from_attributes = True
