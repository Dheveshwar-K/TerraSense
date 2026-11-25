from datetime import datetime
from typing import Any, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class InvestigationCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    line_code: str = Field(..., min_length=2, max_length=10)
    parameter_id: Optional[int] = Field(default=None, gt=0)
    defect_category_id: Optional[int] = Field(default=None, gt=0)
    lag_hours: int = Field(default=12, ge=0, le=168)
    correlation_stat: Optional[float] = None
    p_value: Optional[float] = None
    five_why_analysis: list[str] = Field(default_factory=list)
    fishbone_factors: dict[str, str] = Field(default_factory=dict)
    findings: Optional[str] = Field(default=None, max_length=4000)
    conclusion: Optional[str] = Field(default=None, max_length=4000)


class InvestigationUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=200)
    five_why_analysis: Optional[list[str]] = None
    fishbone_factors: Optional[dict[str, str]] = None
    findings: Optional[str] = Field(default=None, max_length=4000)
    conclusion: Optional[str] = Field(default=None, max_length=4000)
    status: Optional[Literal["IN_PROGRESS", "VALIDATED", "CLOSED"]] = None
    expected_version: Optional[int] = None


class InvestigationResponse(BaseModel):
    id: int
    investigation_number: str
    title: str
    line_code: str
    parameter_id: Optional[int] = None
    defect_category_id: Optional[int] = None
    lag_hours: int
    correlation_stat: Optional[float] = None
    p_value: Optional[float] = None
    five_why_analysis: Any
    fishbone_factors: Any
    findings: Optional[str] = None
    conclusion: Optional[str] = None
    status: str
    version: int = 1
    investigator_name: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
