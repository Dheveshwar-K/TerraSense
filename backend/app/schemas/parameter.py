from typing import Optional
from datetime import datetime
from pydantic import BaseModel

class ParameterBase(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    category: str = "PHYSICAL"
    unit: str
    frequency: str = "HOURLY"
    applicable_lines: str = "D1,D2,D3,D4"
    target_value: float
    lsl: float
    usl: float
    lcl_historical: Optional[float] = None
    ucl_historical: Optional[float] = None
    testing_method: Optional[str] = None
    data_validation_min: Optional[float] = None
    data_validation_max: Optional[float] = None
    is_active: bool = True

class ParameterCreate(ParameterBase):
    pass

class ParameterUpdate(BaseModel):
    name: Optional[str] = None
    target_value: Optional[float] = None
    lsl: Optional[float] = None
    usl: Optional[float] = None
    testing_method: Optional[str] = None
    revision_reason: Optional[str] = None

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

    class Config:
        from_attributes = True

class ParameterResponse(ParameterBase):
    id: int
    current_revision: int

    class Config:
        from_attributes = True
