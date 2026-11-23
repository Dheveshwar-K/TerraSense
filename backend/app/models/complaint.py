from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base

class CustomerComplaint(Base):
    __tablename__ = "customer_complaints"

    id = Column(Integer, primary_key=True, index=True)
    complaint_number = Column(String(50), unique=True, index=True, nullable=False)
    customer_name = Column(String(100), nullable=False, index=True)
    received_date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    product_id = Column(Integer, ForeignKey("casting_products.id"), nullable=False)
    defect_category_id = Column(Integer, ForeignKey("defect_categories.id"), nullable=False)
    batch_number = Column(String(50), nullable=True)
    line_code = Column(String(10), nullable=False)  # D1, D2, D3, D4
    affected_qty = Column(Integer, nullable=False)
    severity = Column(String(20), default="HIGH")  # LOW, MEDIUM, HIGH, CRITICAL
    description = Column(Text, nullable=False)
    
    # 8D Discipline Fields
    d1_team = Column(String(255), nullable=True)
    d2_problem = Column(Text, nullable=True)
    d3_containment = Column(Text, nullable=True)
    d4_root_cause = Column(Text, nullable=True)
    d5_corrective_action = Column(Text, nullable=True)
    d6_validation = Column(Text, nullable=True)
    d7_preventive_action = Column(Text, nullable=True)
    d8_closure = Column(Text, nullable=True)
    
    responsible_person = Column(String(100), nullable=True)
    due_date = Column(String(10), nullable=True)
    status = Column(String(20), default="OPEN")  # OPEN, INVESTIGATION, CAPA_PENDING, CLOSED
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    product = relationship("CastingProduct")
    defect_category = relationship("DefectCategory")
