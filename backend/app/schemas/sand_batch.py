import math
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class SandBatchCreate(BaseModel):
    line_code: str = Field(..., min_length=2, max_length=10)
    muller_id: str = Field(default="Muller-1", min_length=2, max_length=30)
    batch_weight_kg: float = Field(default=2000.0, gt=0)
    bentonite_addition_kg: float = Field(default=25.0, ge=0)
    coal_dust_addition_kg: float = Field(default=12.0, ge=0)
    new_sand_addition_kg: float = Field(default=100.0, ge=0)
    return_sand_kg: float = Field(default=1863.0, ge=0)
    water_addition_liters: float = Field(default=34.0, ge=0)
    cycle_time_seconds: int = Field(default=120, gt=0, le=3600)
    notes: Optional[str] = Field(default=None, max_length=1000)

    @field_validator(
        "batch_weight_kg",
        "bentonite_addition_kg",
        "coal_dust_addition_kg",
        "new_sand_addition_kg",
        "return_sand_kg",
        "water_addition_liters",
    )
    @classmethod
    def check_finite(cls, v: float) -> float:
        if not math.isfinite(v):
            raise ValueError("Batch numeric inputs must be finite")
        return v


class SandBatchResponse(BaseModel):
    id: int
    batch_number: str
    line_code: str
    muller_id: str
    batch_weight_kg: float
    bentonite_addition_kg: float
    coal_dust_addition_kg: float
    new_sand_addition_kg: float
    return_sand_kg: float
    water_addition_liters: float
    cycle_time_seconds: int
    operator_id: Optional[int] = None
    timestamp: datetime
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
