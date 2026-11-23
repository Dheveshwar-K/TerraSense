from typing import Optional
from datetime import datetime
from pydantic import BaseModel

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
    timestamp: datetime
    acknowledged_by_name: Optional[str] = None
    resolved_by_name: Optional[str] = None
    resolution_notes: Optional[str] = None

    class Config:
        from_attributes = True

class AlertActionRequest(BaseModel):
    notes: Optional[str] = None
