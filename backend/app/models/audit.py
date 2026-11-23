from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Text
from app.core.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    user_id = Column(Integer, nullable=True, index=True)
    user_name = Column(String(100), nullable=False, default="System")
    user_role = Column(String(30), nullable=False, default="system")
    
    action = Column(String(30), nullable=False, index=True)  # CREATE, UPDATE, DELETE, APPROVE, REJECT, CORRECTION, EXPORT, LOGIN
    entity_type = Column(String(50), nullable=False, index=True)  # SandTestRecord, Parameter, Specification, Rejection, Complaint, Alert, User
    entity_id = Column(String(50), nullable=True)
    
    old_value = Column(Text, nullable=True)  # JSON text
    new_value = Column(Text, nullable=True)  # JSON text
    reason = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    request_id = Column(String(100), nullable=True)
