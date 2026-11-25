from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class AlertResponse(BaseModel):
    id: int
    alert_code: str
    line_code: str
    parameter_name: Optional[str] = None
    parameter_code: Optional[str] = None
    alert_type: str
    severity: str
    description: str
    nelson_rule_triggered: Optional[str] = None
    status: str
    version: int = 1
    timestamp: datetime
    acknowledged_by_name: Optional[str] = None
    resolved_by_name: Optional[str] = None
    resolution_notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AlertActionRequest(BaseModel):
    notes: Optional[str] = Field(default=None, max_length=1000)
    expected_version: Optional[int] = None
