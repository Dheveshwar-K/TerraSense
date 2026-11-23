from typing import Optional
from datetime import datetime
from pydantic import BaseModel

class ComplaintCreate(BaseModel):
    customer_name: str
    received_date: str
    product_id: int
    defect_category_id: int
    batch_number: Optional[str] = None
    line_code: str
    affected_qty: int
    severity: str = "HIGH"
    description: str

class ComplaintUpdate8D(BaseModel):
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
    status: Optional[str] = None

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

    class Config:
        from_attributes = True
