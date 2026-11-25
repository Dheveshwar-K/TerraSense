import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_client_ip, get_current_user, log_audit, require_role
from app.core.database import get_db
from app.models.line import ProductionLine
from app.models.rejection import CastingProduct, DefectCategory, RejectionRecord
from app.models.user import User
from app.schemas.rejection import DefectCategoryResponse, RejectionCreate, RejectionResponse

router = APIRouter()


@router.get("", response_model=list[RejectionResponse])
def list_rejections(
    line_code: str = None,
    product_id: int = None,
    defect_category_id: int = None,
    start_date: str = None,
    end_date: str = None,
    shift: int = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(RejectionRecord).options(
        joinedload(RejectionRecord.product),
        joinedload(RejectionRecord.defect_category),
        joinedload(RejectionRecord.inspector),
    )
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
    offset = offset if isinstance(offset, int) else 0
    records = query.order_by(RejectionRecord.timestamp.desc(), RejectionRecord.id.desc()).offset(offset).limit(limit).all()

    return [
        RejectionResponse(
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
            batch_number=r.batch_number,
            detection_stage=r.detection_stage,
            severity=r.severity,
            root_cause_candidate=r.root_cause_candidate,
            corrective_action=r.corrective_action,
            responsible_person=r.responsible_person,
            inspector_name=r.inspector.full_name if r.inspector else r.responsible_person,
            status=r.status,
        )
        for r in records
    ]


@router.post("", response_model=RejectionResponse)
def create_rejection_record(
    rej_in: RejectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["quality_engineer", "supervisor", "quality_manager", "admin"])),
    request: Request = None,
):
    line_code = rej_in.line_code.upper()
    line = db.query(ProductionLine).filter(ProductionLine.code == line_code, ProductionLine.is_active == True).first()
    if not line:
        raise HTTPException(status_code=400, detail=f"Invalid or inactive production line '{line_code}'")

    if rej_in.inspected_qty <= 0:
        raise HTTPException(status_code=400, detail="Inspected quantity must be greater than zero")
    if rej_in.rejected_qty < 0:
        raise HTTPException(status_code=400, detail="Rejected quantity cannot be negative")
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
    parsed_date = datetime.strptime(rej_in.production_date, "%Y-%m-%d")
    shift_hour_map = {1: 10, 2: 18, 3: 4}
    rec_ts = parsed_date.replace(hour=shift_hour_map.get(rej_in.shift, 12), minute=0, second=0, tzinfo=timezone.utc)

    rej_num = f"REJ-{line_code}-{rej_in.production_date.replace('-', '')}-{now.strftime('%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"

    rec = RejectionRecord(
        rejection_number=rej_num,
        production_date=rej_in.production_date,
        line_code=line_code,
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
        responsible_person=rej_in.responsible_person or current_user.full_name,
        inspector_id=current_user.id,
        status="RECORDED",
        timestamp=rec_ts,
    )
    db.add(rec)
    db.flush()

    log_audit(
        db,
        current_user,
        "CREATE",
        "RejectionRecord",
        str(rec.id),
        new_value={
            "rejection_number": rec.rejection_number,
            "line_code": rec.line_code,
            "rejected_qty": rec.rejected_qty,
            "inspected_qty": rec.inspected_qty,
            "rate": rejection_rate,
            "defect": defect.name,
        },
        reason="Casting rejection logging",
        ip_address=get_client_ip(request),
        commit=False,
    )
    db.commit()
    db.refresh(rec)

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
        batch_number=rec.batch_number,
        detection_stage=rec.detection_stage,
        severity=rec.severity,
        root_cause_candidate=rec.root_cause_candidate,
        corrective_action=rec.corrective_action,
        responsible_person=rec.responsible_person,
        inspector_name=current_user.full_name,
        status=rec.status,
    )


@router.get("/defects", response_model=list[DefectCategoryResponse])
def get_defect_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(DefectCategory).order_by(DefectCategory.name).all()


@router.get("/products")
def get_products(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    prods = db.query(CastingProduct).order_by(CastingProduct.part_name).all()
    return [
        {
            "id": p.id,
            "part_number": p.part_number,
            "part_name": p.part_name,
            "customer_name": p.customer_name,
            "material_grade": p.material_grade,
        }
        for p in prods
    ]


@router.get("/pareto")
def get_defect_pareto(
    line_code: str = Query("ALL"),
    start_date: str = None,
    end_date: str = None,
    shift: int = None,
    product_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    norm_line = line_code.upper() if isinstance(line_code, str) and line_code else "ALL"
    query = db.query(
        DefectCategory.id,
        DefectCategory.name,
        DefectCategory.code,
        func.sum(RejectionRecord.rejected_qty).label("total_rejected"),
    ).join(RejectionRecord, DefectCategory.id == RejectionRecord.defect_category_id)

    if norm_line != "ALL":
        query = query.filter(RejectionRecord.line_code == norm_line)
    if start_date:
        query = query.filter(RejectionRecord.production_date >= start_date)
    if end_date:
        query = query.filter(RejectionRecord.production_date <= end_date)
    if shift:
        query = query.filter(RejectionRecord.shift == shift)
    if product_id:
        query = query.filter(RejectionRecord.product_id == product_id)

    results = (
        query.group_by(DefectCategory.id, DefectCategory.name, DefectCategory.code)
        .order_by(func.sum(RejectionRecord.rejected_qty).desc(), DefectCategory.code.asc())
        .all()
    )

    grand_total = int(sum((r.total_rejected or 0) for r in results)) if results else 0
    cum_pct = 0.0

    pareto_items = []
    for r in results:
        count = int(r.total_rejected or 0)
        pct = (count / grand_total * 100.0) if grand_total > 0 else 0.0
        cum_pct += pct
        pareto_items.append({
            "defect_id": r.id,
            "defect_name": r.name,
            "defect_code": r.code,
            "rejected_qty": count,
            "percentage": round(pct, 2),
            "cumulative_percentage": round(min(cum_pct, 100.0), 2),
        })

    return {
        "line_code": norm_line,
        "total_rejected": grand_total,
        "defects_count": len(pareto_items),
        "items": pareto_items,
    }
