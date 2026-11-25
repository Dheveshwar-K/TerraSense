from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base


class QualityAlert(Base):
    __tablename__ = "quality_alerts"

    id = Column(Integer, primary_key=True, index=True)
    alert_code = Column(String(50), unique=True, index=True, nullable=False)
    line_code = Column(String(10), nullable=False, index=True)  # D1, D2, D3, D4
    parameter_id = Column(Integer, ForeignKey("parameters.id"), nullable=True)
    record_id = Column(Integer, ForeignKey("sand_test_records.id"), nullable=True)

    alert_type = Column(String(30), nullable=False)  # SPEC_VIOLATION, SPC_RULE_VIOLATION, MISSING_TEST, REJECTION_SPIKE
    severity = Column(String(20), nullable=False, default="WARNING")  # INFO, WARNING, CRITICAL
    description = Column(Text, nullable=False)
    nelson_rule_triggered = Column(String(100), nullable=True)
    status = Column(String(20), default="OPEN", index=True)  # OPEN, ACKNOWLEDGED, RESOLVED
    version = Column(Integer, default=1, nullable=False)

    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    acknowledged_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)
    resolved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    resolution_notes = Column(Text, nullable=True)

    parameter = relationship("Parameter")
    record = relationship("SandTestRecord")
    acknowledged_by = relationship("User", foreign_keys=[acknowledged_by_id])
    resolved_by = relationship("User", foreign_keys=[resolved_by_id])
