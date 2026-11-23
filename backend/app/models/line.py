from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime
from app.core.database import Base

class ProductionLine(Base):
    __tablename__ = "production_lines"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(10), unique=True, index=True, nullable=False)  # D1, D2, D3, D4
    name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    molding_type = Column(String(50), default="High-Pressure Green Sand")
    capacity_tph = Column(Float, default=45.0)  # Tons per hour
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
