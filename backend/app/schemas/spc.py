from typing import Optional, Any
from pydantic import BaseModel

class SPCOptions(BaseModel):
    line_code: str
    parameter_code: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    shift: Optional[int] = None
    chart_type: str = "IMR"  # IMR, XBAR_R, P_CHART

class CapabilityOptions(BaseModel):
    line_code: str
    parameter_code: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
