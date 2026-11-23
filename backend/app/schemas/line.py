from typing import Optional
from pydantic import BaseModel

class LineResponse(BaseModel):
    id: int
    code: str
    name: str
    description: Optional[str] = None
    molding_type: str
    capacity_tph: float
    is_active: bool

    class Config:
        from_attributes = True
