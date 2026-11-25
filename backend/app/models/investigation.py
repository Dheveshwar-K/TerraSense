from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base


class RootCauseInvestigation(Base):
    __tablename__ = "root_cause_investigations"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    investigation_number = Column(String(50), unique=True, index=True, nullable=False)
    line_code = Column(String(10), nullable=False)
    parameter_id = Column(Integer, ForeignKey("parameters.id"), nullable=True)
    defect_category_id = Column(Integer, ForeignKey("defect_categories.id"), nullable=True)

    lag_hours = Column(Integer, default=12)
    correlation_stat = Column(Float, nullable=True)
    p_value = Column(Float, nullable=True)

    five_why_analysis = Column(Text, nullable=True)  # JSON text
    fishbone_factors = Column(Text, nullable=True)   # JSON text: Machine, Method, Material, Man, Measurement, Milieu
    findings = Column(Text, nullable=True)
    conclusion = Column(Text, nullable=True)
    status = Column(String(20), default="IN_PROGRESS")  # IN_PROGRESS, VALIDATED, CLOSED
    version = Column(Integer, default=1, nullable=False)
    investigator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    parameter = relationship("Parameter")
    defect_category = relationship("DefectCategory")
    investigator = relationship("User")
