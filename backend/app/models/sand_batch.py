from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from app.core.database import Base

class SandBatch(Base):
    __tablename__ = "sand_batches"

    id = Column(Integer, primary_key=True, index=True)
    batch_number = Column(String(50), unique=True, index=True, nullable=False)
    line_code = Column(String(10), nullable=False, index=True)  # D1, D2, D3, D4
    muller_id = Column(String(30), nullable=False, default="Muller-1")
    batch_weight_kg = Column(Float, default=2000.0)
    bentonite_addition_kg = Column(Float, default=25.0)
    coal_dust_addition_kg = Column(Float, default=12.0)
    new_sand_addition_kg = Column(Float, default=100.0)
    return_sand_kg = Column(Float, default=1863.0)
    water_addition_liters = Column(Float, default=34.0)
    cycle_time_seconds = Column(Integer, default=120)
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    notes = Column(Text, nullable=True)
