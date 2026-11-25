from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, CheckConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base


class Parameter(Base):
    __tablename__ = "parameters"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(30), unique=True, index=True, nullable=False)  # MOISTURE, COMPACT, GCS, PERM, etc.
    name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    category = Column(String(20), nullable=False, default="PHYSICAL")  # PHYSICAL, CHEMICAL
    unit = Column(String(20), nullable=False)  # %, N/cm², Perm No., etc.
    frequency = Column(String(20), nullable=False, default="HOURLY")  # HOURLY, SHIFT, DAILY
    applicable_lines = Column(String(50), default="D1,D2,D3,D4")

    # Specification limits (Engineering criteria)
    target_value = Column(Float, nullable=False)
    lsl = Column(Float, nullable=False)  # Lower Spec Limit
    usl = Column(Float, nullable=False)  # Upper Spec Limit

    # Statistical Control Limits (Historical reference baselines)
    lcl_historical = Column(Float, nullable=True)
    ucl_historical = Column(Float, nullable=True)

    current_revision = Column(Integer, default=1, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    testing_method = Column(String(100), nullable=True)
    data_validation_min = Column(Float, nullable=True)
    data_validation_max = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    revisions = relationship("ParameterSpecification", back_populates="parameter", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("lsl < usl", name="ck_param_lsl_lt_usl"),
        CheckConstraint("target_value >= lsl AND target_value <= usl", name="ck_param_target_in_spec"),
    )


class ParameterSpecification(Base):
    __tablename__ = "parameter_specifications"

    id = Column(Integer, primary_key=True, index=True)
    parameter_id = Column(Integer, ForeignKey("parameters.id"), nullable=False, index=True)
    revision_number = Column(Integer, nullable=False)
    effective_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    target_value = Column(Float, nullable=False)
    lsl = Column(Float, nullable=False)
    usl = Column(Float, nullable=False)
    change_reason = Column(Text, nullable=False)
    approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    parameter = relationship("Parameter", back_populates="revisions")
