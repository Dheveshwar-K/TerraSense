import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_client_ip, get_current_user, log_audit, require_role
from app.core.database import get_db
from app.models.investigation import RootCauseInvestigation
from app.models.line import ProductionLine
from app.models.user import User
from app.schemas.investigation import (
    InvestigationCreate,
    InvestigationResponse,
    InvestigationUpdate,
)

router = APIRouter()


def _serialize_investigation(inv: RootCauseInvestigation) -> InvestigationResponse:
    try:
        whys = json.loads(inv.five_why_analysis) if inv.five_why_analysis else []
    except Exception:
        whys = [inv.five_why_analysis] if inv.five_why_analysis else []

    try:
        fishbone = json.loads(inv.fishbone_factors) if inv.fishbone_factors else {}
    except Exception:
        fishbone = {}

    return InvestigationResponse(
        id=inv.id,
        investigation_number=inv.investigation_number,
        title=inv.title,
        line_code=inv.line_code,
        parameter_id=inv.parameter_id,
        defect_category_id=inv.defect_category_id,
        lag_hours=inv.lag_hours,
        correlation_stat=inv.correlation_stat,
        p_value=inv.p_value,
        five_why_analysis=whys,
        fishbone_factors=fishbone,
        findings=inv.findings,
        conclusion=inv.conclusion,
        status=inv.status,
        version=inv.version or 1,
        investigator_name=inv.investigator.full_name if inv.investigator else None,
        created_at=inv.created_at,
        updated_at=inv.updated_at,
    )


@router.get("", response_model=list[InvestigationResponse])
def list_investigations(
    line_code: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(RootCauseInvestigation).options(joinedload(RootCauseInvestigation.investigator))
    if line_code and line_code != "ALL":
        query = query.filter(RootCauseInvestigation.line_code == line_code.upper())
    records = query.order_by(RootCauseInvestigation.created_at.desc(), RootCauseInvestigation.id.desc()).limit(50).all()
    return [_serialize_investigation(r) for r in records]


@router.post("", response_model=InvestigationResponse, status_code=status.HTTP_201_CREATED)
def create_investigation(
    inv_in: InvestigationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["quality_engineer", "supervisor", "quality_manager", "admin"])),
    request: Request = None,
):
    line_code = inv_in.line_code.upper()
    line = db.query(ProductionLine).filter(ProductionLine.code == line_code, ProductionLine.is_active == True).first()
    if not line:
        raise HTTPException(status_code=400, detail=f"Invalid or inactive production line '{line_code}'")

    now = datetime.now(timezone.utc)
    inv_num = f"RCA-{line_code}-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:5].upper()}"

    inv = RootCauseInvestigation(
        investigation_number=inv_num,
        title=inv_in.title.strip(),
        line_code=line_code,
        parameter_id=inv_in.parameter_id,
        defect_category_id=inv_in.defect_category_id,
        lag_hours=inv_in.lag_hours,
        correlation_stat=inv_in.correlation_stat,
        p_value=inv_in.p_value,
        five_why_analysis=json.dumps(inv_in.five_why_analysis),
        fishbone_factors=json.dumps(inv_in.fishbone_factors),
        findings=inv_in.findings,
        conclusion=inv_in.conclusion,
        status="IN_PROGRESS",
        version=1,
        investigator_id=current_user.id,
        created_at=now,
        updated_at=now,
    )
    db.add(inv)
    db.flush()

    log_audit(
        db,
        current_user,
        "CREATE",
        "RootCauseInvestigation",
        str(inv.id),
        new_value={"investigation_number": inv.investigation_number, "title": inv.title, "line": inv.line_code},
        reason="Created structured 5-Why & Ishikawa root-cause dossier",
        ip_address=get_client_ip(request),
        commit=False,
    )
    db.commit()
    db.refresh(inv)
    return _serialize_investigation(inv)


@router.put("/{investigation_id}", response_model=InvestigationResponse)
def update_investigation(
    investigation_id: int,
    inv_up: InvestigationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["quality_engineer", "supervisor", "quality_manager", "admin"])),
    request: Request = None,
):
    inv = (
        db.query(RootCauseInvestigation)
        .options(joinedload(RootCauseInvestigation.investigator))
        .filter(RootCauseInvestigation.id == investigation_id)
        .first()
    )
    if not inv:
        raise HTTPException(status_code=404, detail="Root cause investigation not found")

    if inv_up.expected_version is not None and (inv.version or 1) != inv_up.expected_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Investigation was updated concurrently by another user. Refresh and retry.",
        )

    old_snapshot = {"status": inv.status, "title": inv.title, "version": inv.version}

    if inv_up.title is not None:
        inv.title = inv_up.title.strip()
    if inv_up.five_why_analysis is not None:
        inv.five_why_analysis = json.dumps(inv_up.five_why_analysis)
    if inv_up.fishbone_factors is not None:
        inv.fishbone_factors = json.dumps(inv_up.fishbone_factors)
    if inv_up.findings is not None:
        inv.findings = inv_up.findings
    if inv_up.conclusion is not None:
        inv.conclusion = inv_up.conclusion
    if inv_up.status is not None:
        inv.status = inv_up.status
    inv.version = (inv.version or 1) + 1
    inv.updated_at = datetime.now(timezone.utc)

    log_audit(
        db,
        current_user,
        "UPDATE",
        "RootCauseInvestigation",
        str(inv.id),
        old_value=old_snapshot,
        new_value={"status": inv.status, "title": inv.title, "version": inv.version},
        reason="Updated 5-Why / Ishikawa root cause analysis",
        ip_address=get_client_ip(request),
        commit=False,
    )
    db.commit()
    db.refresh(inv)
    return _serialize_investigation(inv)
