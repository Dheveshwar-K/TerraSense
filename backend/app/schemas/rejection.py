from typing import Optional
from datetime import datetime
from pydantic import BaseModel

class RejectionCreate(BaseModel):
    production_date: str  # YYYY-MM-DD
    line_code: str
    shift: int
    product_id: int
    defect_category_id: int
    rejected_qty: int
    inspected_qty: int
    batch_number: Optional[str] = None
    detection_stage: str = "Visual Shakeout"
    severity: str = "MAJOR"
    root_cause_candidate: Optional[str] = None
    corrective_action: Optional[str] = None
    responsible_person: Optional[str] = None

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
    detection_stage: str
    severity: str
    root_cause_candidate: Optional[str] = None
    corrective_action: Optional[str] = None
    responsible_person: Optional[str] = None
    status: str

    class Config:
        from_attributes = True

class DefectCategoryResponse(BaseModel):
    id: int
    code: str
    name: str
    description: Optional[str] = None
    potential_sand_causes: Optional[str] = None

    class Config:
        from_attributes = True
