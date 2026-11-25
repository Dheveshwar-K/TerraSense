import math
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ValueEntry(BaseModel):
    parameter_id: int = Field(..., gt=0)
    measured_value: float

    @field_validator("measured_value")
    @classmethod
    def check_finite(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError("measured_value must be a finite number")
        return v


class SandTestCreate(BaseModel):
    line_code: str = Field(..., min_length=2, max_length=10)
    test_type: Literal["HOURLY_PHYSICAL", "SHIFT_CHEMICAL"] = "HOURLY_PHYSICAL"
    test_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    shift: int = Field(..., ge=1, le=3)
    test_hour: int = Field(..., ge=1, le=24)
    batch_number: Optional[str] = Field(default=None, max_length=50)
    notes: Optional[str] = Field(default=None, max_length=1000)
    values: list[ValueEntry] = Field(..., min_length=1)

    @field_validator("test_date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        datetime.strptime(v, "%Y-%m-%d")
        return v


class CorrectionRequestCreate(BaseModel):
    value_id: int = Field(..., gt=0)
    requested_value: float
    reason: str = Field(..., min_length=5, max_length=1000)

    @field_validator("requested_value")
    @classmethod
    def check_finite(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError("requested_value must be a finite number")
        return v


class CorrectionReviewRequest(BaseModel):
    review_notes: Optional[str] = Field(default=None, max_length=1000)


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

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


class CorrectionRequestResponse(BaseModel):
    id: int
    value_id: int
    test_number: Optional[str] = None
    line_code: Optional[str] = None
    parameter_name: Optional[str] = None
    current_value: Optional[float] = None
    requested_value: float
    unit: Optional[str] = None
    reason: str
    status: str
    requested_by_name: Optional[str] = None
    reviewed_by_name: Optional[str] = None
    review_notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
