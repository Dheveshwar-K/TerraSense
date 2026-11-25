from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ComplaintCreate(BaseModel):
    customer_name: str = Field(..., min_length=2, max_length=100)
    received_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    product_id: int = Field(..., gt=0)
    defect_category_id: int = Field(..., gt=0)
    batch_number: Optional[str] = Field(default=None, max_length=50)
    line_code: str = Field(..., min_length=2, max_length=10)
    affected_qty: int = Field(..., gt=0)
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "HIGH"
    description: str = Field(..., min_length=5, max_length=2000)

    @field_validator("received_date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        datetime.strptime(v, "%Y-%m-%d")
        return v


class ComplaintUpdate8D(BaseModel):
    d1_team: Optional[str] = Field(default=None, max_length=255)
    d2_problem: Optional[str] = Field(default=None, max_length=2000)
    d3_containment: Optional[str] = Field(default=None, max_length=2000)
    d4_root_cause: Optional[str] = Field(default=None, max_length=2000)
    d5_corrective_action: Optional[str] = Field(default=None, max_length=2000)
    d6_validation: Optional[str] = Field(default=None, max_length=2000)
    d7_preventive_action: Optional[str] = Field(default=None, max_length=2000)
    d8_closure: Optional[str] = Field(default=None, max_length=2000)
    responsible_person: Optional[str] = Field(default=None, max_length=100)
    due_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    status: Optional[Literal["OPEN", "UNDER_INVESTIGATION", "CAPA_PENDING", "CLOSED"]] = None
    expected_version: Optional[int] = None


class ComplaintResponse(BaseModel):
    id: int
    complaint_number: str
    customer_name: str
    received_date: str
    product_name: str
    defect_name: str
    batch_number: Optional[str] = None
    line_code: str
    affected_qty: int
    severity: str
    description: str
    status: str
    version: int = 1
    d1_team: Optional[str] = None
    d2_problem: Optional[str] = None
    d3_containment: Optional[str] = None
    d4_root_cause: Optional[str] = None
    d5_corrective_action: Optional[str] = None
    d6_validation: Optional[str] = None
    d7_preventive_action: Optional[str] = None
    d8_closure: Optional[str] = None
    responsible_person: Optional[str] = None
    due_date: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
