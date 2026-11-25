from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, UniqueConstraint, CheckConstraint, Index
from sqlalchemy.orm import relationship
from app.core.database import Base


class SandTestRecord(Base):
    __tablename__ = "sand_test_records"

    id = Column(Integer, primary_key=True, index=True)
    test_number = Column(String(50), unique=True, index=True, nullable=False)
    line_code = Column(String(10), nullable=False, index=True)  # D1, D2, D3, D4
    test_type = Column(String(20), nullable=False, default="HOURLY_PHYSICAL")  # HOURLY_PHYSICAL, SHIFT_CHEMICAL
    test_date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    shift = Column(Integer, nullable=False, index=True)  # 1, 2, 3
    test_hour = Column(Integer, nullable=False, index=True)  # 1..24
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    batch_number = Column(String(50), nullable=True)
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(20), default="CONFORMING")  # CONFORMING, WARNING, OUT_OF_SPEC
    is_missing = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationship to individual parameter values
    values = relationship("SandTestValue", back_populates="record", cascade="all, delete-orphan")
    operator = relationship("User")

    __table_args__ = (
        UniqueConstraint("line_code", "test_date", "shift", "test_hour", "test_type", name="uq_line_date_shift_hour_type"),
        CheckConstraint("shift IN (1, 2, 3)", name="ck_sand_test_shift_valid"),
        CheckConstraint("test_hour >= 1 AND test_hour <= 24", name="ck_sand_test_hour_valid"),
        Index("ix_sand_test_line_date_ts", "line_code", "test_date", "timestamp"),
    )


class SandTestValue(Base):
    __tablename__ = "sand_test_values"

    id = Column(Integer, primary_key=True, index=True)
    record_id = Column(Integer, ForeignKey("sand_test_records.id"), nullable=False, index=True)
    parameter_id = Column(Integer, ForeignKey("parameters.id"), nullable=False, index=True)

    measured_value = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)
    specification_revision = Column(Integer, default=1)
    status = Column(String(20), default="OK")  # OK, WARNING, OUT_OF_SPEC

    # Audit & correction fields
    is_corrected = Column(Boolean, default=False)
    original_value = Column(Float, nullable=True)
    correction_reason = Column(Text, nullable=True)
    corrected_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    corrected_at = Column(DateTime, nullable=True)

    record = relationship("SandTestRecord", back_populates="values")
    parameter = relationship("Parameter")
    corrected_by = relationship("User", foreign_keys=[corrected_by_id])

    __table_args__ = (
        Index("ix_sand_val_param_record", "parameter_id", "record_id"),
    )


class TestCorrectionRequest(Base):
    __tablename__ = "test_correction_requests"

    id = Column(Integer, primary_key=True, index=True)
    value_id = Column(Integer, ForeignKey("sand_test_values.id"), nullable=False, index=True)
    requested_value = Column(Float, nullable=False)
    reason = Column(Text, nullable=False)
    requested_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(20), default="PENDING")  # PENDING, APPROVED, REJECTED
    reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    value = relationship("SandTestValue")
    requested_by = relationship("User", foreign_keys=[requested_by_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])
