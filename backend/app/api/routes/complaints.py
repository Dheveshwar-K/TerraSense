import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_client_ip, get_current_user, log_audit, require_role
from app.core.database import get_db
from app.models.complaint import CustomerComplaint
from app.models.line import ProductionLine
from app.models.rejection import CastingProduct, DefectCategory
from app.models.user import User
from app.schemas.complaint import ComplaintCreate, ComplaintResponse, ComplaintUpdate8D

router = APIRouter()


def _to_complaint_response(c: CustomerComplaint) -> ComplaintResponse:
    return ComplaintResponse(
        id=c.id,
        complaint_number=c.complaint_number,
        customer_name=c.customer_name,
        received_date=c.received_date,
        product_name=c.product.part_name if c.product else "Unknown",
        defect_name=c.defect_category.name if c.defect_category else "Unknown",
        batch_number=c.batch_number,
        line_code=c.line_code,
        affected_qty=c.affected_qty,
        severity=c.severity,
        description=c.description,
        status=c.status,
        version=c.version or 1,
        d1_team=c.d1_team,
        d2_problem=c.d2_problem,
        d3_containment=c.d3_containment,
        d4_root_cause=c.d4_root_cause,
        d5_corrective_action=c.d5_corrective_action,
        d6_validation=c.d6_validation,
        d7_preventive_action=c.d7_preventive_action,
        d8_closure=c.d8_closure,
        responsible_person=c.responsible_person,
        due_date=c.due_date,
    )


@router.get("", response_model=list[ComplaintResponse])
def list_complaints(
    status: str = None,
    customer_name: str = None,
    line_code: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(CustomerComplaint).options(
        joinedload(CustomerComplaint.product),
        joinedload(CustomerComplaint.defect_category),
    )
    if status and status != "ALL":
        query = query.filter(CustomerComplaint.status == status.upper())
    if customer_name:
        query = query.filter(CustomerComplaint.customer_name.ilike(f"%{customer_name}%"))
    if line_code and line_code != "ALL":
        query = query.filter(CustomerComplaint.line_code == line_code.upper())

    records = query.order_by(CustomerComplaint.created_at.desc(), CustomerComplaint.id.desc()).all()
    return [_to_complaint_response(c) for c in records]


@router.post("", response_model=ComplaintResponse)
def create_complaint(
    comp_in: ComplaintCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["quality_engineer", "quality_manager", "admin"])),
    request: Request = None,
):
    line_code = comp_in.line_code.upper()
    line = db.query(ProductionLine).filter(ProductionLine.code == line_code, ProductionLine.is_active == True).first()
    if not line:
        raise HTTPException(status_code=400, detail=f"Invalid or inactive production line '{line_code}'")

    prod = db.query(CastingProduct).filter(CastingProduct.id == comp_in.product_id).first()
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")
    defect = db.query(DefectCategory).filter(DefectCategory.id == comp_in.defect_category_id).first()
    if not defect:
        raise HTTPException(status_code=404, detail="Defect category not found")

    now = datetime.now(timezone.utc)
    comp_num = f"CMP-{now.strftime('%Y')}-{now.strftime('%m%d%H%M')}-{uuid.uuid4().hex[:4].upper()}"

    c = CustomerComplaint(
        complaint_number=comp_num,
        customer_name=comp_in.customer_name,
        received_date=comp_in.received_date,
        product_id=comp_in.product_id,
        defect_category_id=comp_in.defect_category_id,
        batch_number=comp_in.batch_number,
        line_code=line_code,
        affected_qty=comp_in.affected_qty,
        severity=comp_in.severity.upper(),
        description=comp_in.description,
        status="OPEN",
        version=1,
    )
    db.add(c)
    db.flush()

    log_audit(
        db,
        current_user,
        "CREATE",
        "CustomerComplaint",
        str(c.id),
        new_value={"number": c.complaint_number, "customer": c.customer_name, "defect": defect.name},
        reason="Customer quality complaint registered",
        ip_address=get_client_ip(request),
        commit=False,
    )
    db.commit()
    db.refresh(c)
    return _to_complaint_response(c)


@router.put("/{complaint_id}/8d", response_model=ComplaintResponse)
def update_complaint_8d(
    complaint_id: int,
    update_in: ComplaintUpdate8D,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["quality_engineer", "quality_manager", "admin"])),
    request: Request = None,
):
    c = (
        db.query(CustomerComplaint)
        .options(
            joinedload(CustomerComplaint.product),
            joinedload(CustomerComplaint.defect_category),
        )
        .filter(CustomerComplaint.id == complaint_id)
        .first()
    )
    if not c:
        raise HTTPException(status_code=404, detail="Complaint not found")

    if update_in.expected_version is not None and (c.version or 1) != update_in.expected_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="8D CAPA dossier was modified concurrently by another user. Refresh and retry.",
        )

    old_status = c.status
    old_version = c.version or 1

    if update_in.d1_team is not None:
        c.d1_team = update_in.d1_team
    if update_in.d2_problem is not None:
        c.d2_problem = update_in.d2_problem
    if update_in.d3_containment is not None:
        c.d3_containment = update_in.d3_containment
    if update_in.d4_root_cause is not None:
        c.d4_root_cause = update_in.d4_root_cause
    if update_in.d5_corrective_action is not None:
        c.d5_corrective_action = update_in.d5_corrective_action
    if update_in.d6_validation is not None:
        c.d6_validation = update_in.d6_validation
    if update_in.d7_preventive_action is not None:
        c.d7_preventive_action = update_in.d7_preventive_action
    if update_in.d8_closure is not None:
        c.d8_closure = update_in.d8_closure
    if update_in.responsible_person is not None:
        c.responsible_person = update_in.responsible_person
    if update_in.due_date is not None:
        c.due_date = update_in.due_date
    if update_in.status is not None:
        c.status = update_in.status.upper()

    c.version = old_version + 1

    log_audit(
        db,
        current_user,
        "UPDATE_8D",
        "CustomerComplaint",
        str(c.id),
        old_value={"status": old_status, "version": old_version},
        new_value={"status": c.status, "version": c.version, "updated_8d_disciplines": True},
        reason="Updated 8D CAPA investigation findings",
        ip_address=get_client_ip(request),
        commit=False,
    )
    db.commit()
    db.refresh(c)
    return _to_complaint_response(c)
