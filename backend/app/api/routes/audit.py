from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import get_client_ip, log_audit, require_role
from app.core.database import get_db
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.audit import AuditLogResponse
from app.services.audit_service import verify_audit_chain

router = APIRouter()


@router.get("", response_model=list[AuditLogResponse])
def list_audit_logs(
    entity_type: str = None,
    action: str = None,
    start_date: str = None,
    end_date: str = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["quality_engineer", "supervisor", "quality_manager", "admin"])),
):
    query = db.query(AuditLog)
    if entity_type and entity_type != "ALL":
        query = query.filter(AuditLog.entity_type == entity_type)
    if action and action != "ALL":
        query = query.filter(AuditLog.action == action.upper())
    if start_date:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        query = query.filter(AuditLog.timestamp >= start_dt)
    if end_date:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
        query = query.filter(AuditLog.timestamp < end_dt)

    limit = limit if isinstance(limit, int) else 100
    offset = offset if isinstance(offset, int) else 0
    return (
        query.order_by(AuditLog.sequence_no.desc(), AuditLog.timestamp.desc(), AuditLog.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get("/verify")
def verify_audit_trail_integrity(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["quality_engineer", "quality_manager", "admin"])),
    request: Request = None,
):
    """Verifies the SHA-256 hash chain across all audit records and logs the verification event."""
    result = verify_audit_chain(db)
    log_audit(
        db,
        current_user,
        "VERIFY_AUDIT",
        "AuditLog",
        "CHAIN",
        new_value={"valid": result["valid"], "checked": result["total_records"]},
        reason="Audit trail hash-chain integrity verification executed",
        ip_address=get_client_ip(request),
        outcome="SUCCESS" if result["valid"] else "FAILURE",
    )
    return result
