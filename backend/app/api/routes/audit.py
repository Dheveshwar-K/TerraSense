from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.audit import AuditLog
from app.models.user import User
from app.schemas.audit import AuditLogResponse
from app.api.deps import get_current_user, require_role

router = APIRouter()

@router.get("", response_model=list[AuditLogResponse])
def list_audit_logs(
    entity_type: str = None,
    action: str = None,
    start_date: str = None,
    end_date: str = None,
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(AuditLog)
    if entity_type and entity_type != "ALL":
        query = query.filter(AuditLog.entity_type == entity_type)
    if action and action != "ALL":
        query = query.filter(AuditLog.action == action.upper())

    limit = limit if isinstance(limit, int) else 100
    records = query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return records
