from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RejectionCreate(BaseModel):
    production_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    line_code: str = Field(..., min_length=2, max_length=10)
    shift: int = Field(..., ge=1, le=3)
    product_id: int = Field(..., gt=0)
    defect_category_id: int = Field(..., gt=0)
    rejected_qty: int = Field(..., ge=0)
    inspected_qty: int = Field(..., gt=0)
    batch_number: Optional[str] = Field(default=None, max_length=50)
    detection_stage: str = Field(default="Visual Shakeout", max_length=50)
    severity: Literal["MINOR", "MAJOR", "CRITICAL"] = "MAJOR"
    root_cause_candidate: Optional[str] = Field(default=None, max_length=255)
    corrective_action: Optional[str] = Field(default=None, max_length=1000)
    responsible_person: Optional[str] = Field(default=None, max_length=100)

    @field_validator("production_date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        datetime.strptime(v, "%Y-%m-%d")
        return v

    @model_validator(mode="after")
    def validate_quantities(self):
        if self.rejected_qty > self.inspected_qty:
            raise ValueError("rejected_qty cannot exceed inspected_qty")
        return self


class RejectionResponse(BaseModel):
    id: int
    rejection_number: str
    production_date: str
    line_code: str
    shift: int
    product_name: str
    defect_name: str
    defect_code: str
    rejected_qty: int
    inspected_qty: int
    rejection_rate: float
    batch_number: Optional[str] = None
    detection_stage: str
    severity: str
    root_cause_candidate: Optional[str] = None
    corrective_action: Optional[str] = None
    responsible_person: Optional[str] = None
    inspector_name: Optional[str] = None
    status: str

    model_config = ConfigDict(from_attributes=True)


class DefectCategoryResponse(BaseModel):
    id: int
    code: str
    name: str
    description: Optional[str] = None
    potential_sand_causes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
