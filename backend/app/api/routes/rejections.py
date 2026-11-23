from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.models.rejection import RejectionRecord, DefectCategory, CastingProduct
from app.models.user import User
from app.schemas.rejection import RejectionResponse, RejectionCreate, DefectCategoryResponse
from app.api.deps import get_current_user, require_role, log_audit

router = APIRouter()

@router.get("", response_model=list[RejectionResponse])
def list_rejections(
    line_code: str = None,
    product_id: int = None,
    defect_category_id: int = None,
    start_date: str = None,
    end_date: str = None,
    shift: int = None,
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(RejectionRecord)
    if line_code and line_code != "ALL":
        query = query.filter(RejectionRecord.line_code == line_code.upper())
    if product_id:
        query = query.filter(RejectionRecord.product_id == product_id)
    if defect_category_id:
        query = query.filter(RejectionRecord.defect_category_id == defect_category_id)
    if start_date:
        query = query.filter(RejectionRecord.production_date >= start_date)
    if end_date:
        query = query.filter(RejectionRecord.production_date <= end_date)
    if shift:
        query = query.filter(RejectionRecord.shift == shift)

    limit = limit if isinstance(limit, int) else 100
    records = query.order_by(RejectionRecord.timestamp.desc()).limit(limit).all()

    res = []
    for r in records:
        res.append(RejectionResponse(
            id=r.id,
            rejection_number=r.rejection_number,
            production_date=r.production_date,
            line_code=r.line_code,
            shift=r.shift,
            product_name=r.product.part_name if r.product else "Unknown",
            defect_name=r.defect_category.name if r.defect_category else "Unknown",
            defect_code=r.defect_category.code if r.defect_category else "UNK",
            rejected_qty=r.rejected_qty,
            inspected_qty=r.inspected_qty,
            rejection_rate=r.rejection_rate,
            detection_stage=r.detection_stage,
            severity=r.severity,
            root_cause_candidate=r.root_cause_candidate,
            corrective_action=r.corrective_action,
            responsible_person=r.responsible_person,
            status=r.status
        ))
    return res

@router.post("", response_model=RejectionResponse)
def create_rejection_record(
    rej_in: RejectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if rej_in.inspected_qty <= 0:
        raise HTTPException(status_code=400, detail="Inspected quantity must be greater than zero")
    if rej_in.rejected_qty > rej_in.inspected_qty:
        raise HTTPException(status_code=400, detail="Rejected quantity cannot exceed inspected quantity")

    prod = db.query(CastingProduct).filter(CastingProduct.id == rej_in.product_id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Casting product not found")
    defect = db.query(DefectCategory).filter(DefectCategory.id == rej_in.defect_category_id).first()
    if not defect:
        raise HTTPException(status_code=404, detail="Defect category not found")

    rejection_rate = round((rej_in.rejected_qty / rej_in.inspected_qty) * 100.0, 2)
    now = datetime.now(timezone.utc)
    rej_num = f"REJ-{rej_in.line_code.upper()}-{rej_in.production_date.replace('-','')}-{now.strftime('%H%M%S')}"

    rec = RejectionRecord(
        rejection_number=rej_num,
        production_date=rej_in.production_date,
        line_code=rej_in.line_code.upper(),
        shift=rej_in.shift,
        product_id=rej_in.product_id,
        defect_category_id=rej_in.defect_category_id,
        rejected_qty=rej_in.rejected_qty,
        inspected_qty=rej_in.inspected_qty,
        rejection_rate=rejection_rate,
        batch_number=rej_in.batch_number,
        detection_stage=rej_in.detection_stage,
        severity=rej_in.severity,
        root_cause_candidate=rej_in.root_cause_candidate,
        corrective_action=rej_in.corrective_action,
        responsible_person=rej_in.responsible_person,
        status="RECORDED",
        timestamp=now
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    log_audit(
        db, current_user, "CREATE", "RejectionRecord", str(rec.id),
        new_value={"rejection_number": rec.rejection_number, "rate": rejection_rate, "defect": defect.name},
        reason="Manual casting rejection logging"
    )

    return RejectionResponse(
        id=rec.id,
        rejection_number=rec.rejection_number,
        production_date=rec.production_date,
        line_code=rec.line_code,
        shift=rec.shift,
        product_name=prod.part_name,
        defect_name=defect.name,
        defect_code=defect.code,
        rejected_qty=rec.rejected_qty,
        inspected_qty=rec.inspected_qty,
        rejection_rate=rec.rejection_rate,
        detection_stage=rec.detection_stage,
        severity=rec.severity,
        root_cause_candidate=rec.root_cause_candidate,
        corrective_action=rec.corrective_action,
        responsible_person=rec.responsible_person,
        status=rec.status
    )

@router.get("/defects", response_model=list[DefectCategoryResponse])
def get_defect_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(DefectCategory).order_by(DefectCategory.name).all()

@router.get("/products")
def get_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    prods = db.query(CastingProduct).all()
    return [{"id": p.id, "part_number": p.part_number, "part_name": p.part_name, "customer_name": p.customer_name, "material_grade": p.material_grade} for p in prods]

@router.get("/pareto")
def get_defect_pareto(
    line_code: str = Query("ALL"),
    start_date: str = None,
    end_date: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(
        DefectCategory.id,
        DefectCategory.name,
        DefectCategory.code,
        func.sum(RejectionRecord.rejected_qty).label("total_rejected")
    ).join(RejectionRecord, DefectCategory.id == RejectionRecord.defect_category_id)

    if line_code and line_code != "ALL":
        query = query.filter(RejectionRecord.line_code == line_code.upper())
    if start_date:
        query = query.filter(RejectionRecord.production_date >= start_date)
    if end_date:
        query = query.filter(RejectionRecord.production_date <= end_date)

    results = query.group_by(DefectCategory.id, DefectCategory.name, DefectCategory.code).order_by(func.sum(RejectionRecord.rejected_qty).desc()).all()

    grand_total = sum(r.total_rejected for r in results) if results else 0
    cum_pct = 0.0

    pareto_items = []
    for r in results:
        count = int(r.total_rejected)
        pct = (count / grand_total * 100.0) if grand_total > 0 else 0.0
        cum_pct += pct
        pareto_items.append({
            "defect_id": r.id,
            "defect_name": r.name,
            "defect_code": r.code,
            "rejected_qty": count,
            "percentage": round(pct, 2),
            "cumulative_percentage": round(min(cum_pct, 100.0), 2)
        })

    return {
        "line_code": line_code.upper(),
        "total_rejected": grand_total,
        "defects_count": len(pareto_items),
        "items": pareto_items
    }
