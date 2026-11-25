import math
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ParameterBase(BaseModel):
    code: str = Field(..., min_length=2, max_length=30)
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = Field(default=None, max_length=255)
    category: Literal["PHYSICAL", "CHEMICAL"] = "PHYSICAL"
    unit: str = Field(..., min_length=1, max_length=20)
    frequency: Literal["HOURLY", "SHIFT", "DAILY"] = "HOURLY"
    applicable_lines: str = Field(default="D1,D2,D3,D4", max_length=50)
    target_value: float
    lsl: float
    usl: float
    lcl_historical: Optional[float] = None
    ucl_historical: Optional[float] = None
    testing_method: Optional[str] = Field(default=None, max_length=100)
    data_validation_min: Optional[float] = None
    data_validation_max: Optional[float] = None
    is_active: bool = True

    @field_validator("target_value", "lsl", "usl")
    @classmethod
    def check_finite(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError("Specification values must be finite numbers")
        return v

    @model_validator(mode="after")
    def check_spec_bounds(self):
        if self.lsl >= self.usl:
            raise ValueError("Lower Spec Limit (LSL) must be strictly less than Upper Spec Limit (USL)")
        if not (self.lsl <= self.target_value <= self.usl):
            raise ValueError("Target value must lie within [LSL, USL]")
        if (
            self.data_validation_min is not None
            and self.data_validation_max is not None
            and self.data_validation_min >= self.data_validation_max
        ):
            raise ValueError("data_validation_min must be less than data_validation_max")
        return self


class ParameterCreate(ParameterBase):
    pass


class ParameterUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    target_value: Optional[float] = None
    lsl: Optional[float] = None
    usl: Optional[float] = None
    testing_method: Optional[str] = Field(default=None, max_length=100)
    revision_reason: Optional[str] = Field(default=None, max_length=500)
    expected_version: Optional[int] = None

    @field_validator("target_value", "lsl", "usl")
    @classmethod
    def check_finite_opt(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not math.isfinite(v):
            raise ValueError("Specification values must be finite numbers")
        return v


class SpecificationRevisionResponse(BaseModel):
    id: int
    parameter_id: int
    revision_number: int
    effective_date: datetime
    target_value: float
    lsl: float
    usl: float
    change_reason: str
    approved_by_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class ParameterResponse(ParameterBase):
    id: int
    current_revision: int
    version: int = 1

    model_config = ConfigDict(from_attributes=True)
