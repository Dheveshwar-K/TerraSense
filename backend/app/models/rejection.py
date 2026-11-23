from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base

class CastingProduct(Base):
    __tablename__ = "casting_products"

    id = Column(Integer, primary_key=True, index=True)
    part_number = Column(String(50), unique=True, index=True, nullable=False)
    part_name = Column(String(100), nullable=False)
    customer_name = Column(String(100), nullable=False)
    material_grade = Column(String(50), default="EN-GJS-500-7")  # Ductile iron / Grey iron
    weight_kg = Column(Float, default=18.5)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class DefectCategory(Base):
    __tablename__ = "defect_categories"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(30), unique=True, index=True, nullable=False)  # POROSITY, BLOWHOLE, SAND_INCLUSION, etc.
    name = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    potential_sand_causes = Column(Text, nullable=True)

class RejectionRecord(Base):
    __tablename__ = "rejection_records"

    id = Column(Integer, primary_key=True, index=True)
    rejection_number = Column(String(50), unique=True, index=True, nullable=False)
    production_date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    line_code = Column(String(10), nullable=False, index=True)  # D1, D2, D3, D4
    shift = Column(Integer, nullable=False, index=True)  # 1, 2, 3
    product_id = Column(Integer, ForeignKey("casting_products.id"), nullable=False, index=True)
    defect_category_id = Column(Integer, ForeignKey("defect_categories.id"), nullable=False, index=True)
    
    rejected_qty = Column(Integer, nullable=False)
    inspected_qty = Column(Integer, nullable=False)
    rejection_rate = Column(Float, nullable=False)  # (rejected / inspected) * 100
    
    batch_number = Column(String(50), nullable=True)
    detection_stage = Column(String(50), default="Visual Shakeout")  # Shakeout, Shotblast, Machining, Final QC
    severity = Column(String(20), default="MAJOR")  # MINOR, MAJOR, CRITICAL
    root_cause_candidate = Column(String(255), nullable=True)
    corrective_action = Column(Text, nullable=True)
    responsible_person = Column(String(100), nullable=True)
    status = Column(String(20), default="RECORDED")  # RECORDED, INVESTIGATING, CLOSED
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    product = relationship("CastingProduct")
    defect_category = relationship("DefectCategory")
