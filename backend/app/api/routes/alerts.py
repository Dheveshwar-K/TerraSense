from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_client_ip, get_current_user, log_audit, require_role
from app.core.database import get_db
from app.models.alert import QualityAlert
from app.models.user import User
from app.schemas.alert import AlertActionRequest, AlertResponse
from app.services.alert_engine import AlertEngine

router = APIRouter()


@router.get("", response_model=list[AlertResponse])
def list_alerts(
    line_code: str = None,
    status_filter: str = Query(default=None, alias="status"),
    severity: str = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(QualityAlert).options(
        joinedload(QualityAlert.parameter),
        joinedload(QualityAlert.acknowledged_by),
        joinedload(QualityAlert.resolved_by),
    )
    if line_code and line_code != "ALL":
        query = query.filter(QualityAlert.line_code == line_code.upper())
    if status_filter and status_filter != "ALL":
        query = query.filter(QualityAlert.status == status_filter.upper())
    if severity and severity != "ALL":
        query = query.filter(QualityAlert.severity == severity.upper())

    limit = limit if isinstance(limit, int) else 100
    records = query.order_by(QualityAlert.timestamp.desc(), QualityAlert.id.desc()).limit(limit).all()

    return [
        AlertResponse(
            id=a.id,
            alert_code=a.alert_code,
            line_code=a.line_code,
            parameter_name=a.parameter.name if a.parameter else None,
            parameter_code=a.parameter.code if a.parameter else None,
            alert_type=a.alert_type,
            severity=a.severity,
            description=a.description,
            nelson_rule_triggered=a.nelson_rule_triggered,
            status=a.status,
            version=a.version or 1,
            timestamp=a.timestamp,
            acknowledged_by_name=a.acknowledged_by.full_name if a.acknowledged_by else None,
            resolved_by_name=a.resolved_by.full_name if a.resolved_by else None,
            resolution_notes=a.resolution_notes,
        )
        for a in records
    ]


@router.post("/{alert_id}/acknowledge", response_model=dict)
def acknowledge_alert(
    alert_id: int,
    action_in: AlertActionRequest = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    notes = action_in.notes if action_in else None
    expected_version = action_in.expected_version if action_in else None

    existing = db.query(QualityAlert).filter(QualityAlert.id == alert_id).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Alert not found")
    old_status = existing.status

    try:
        alert = AlertEngine.acknowledge_alert(
            db,
            alert_id,
            current_user.id,
            notes=notes,
            expected_version=expected_version,
        )
    except ValueError as exc:
        if str(exc) == "VERSION_CONFLICT":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Alert was updated concurrently. Refresh and retry.")
        if str(exc) == "ALREADY_RESOLVED":
            raise HTTPException(status_code=400, detail="Alert is already resolved")
        raise

    log_audit(
        db,
        current_user,
        "ACKNOWLEDGE",
        "QualityAlert",
        str(alert.id),
        old_value={"status": old_status},
        new_value={"status": "ACKNOWLEDGED", "notes": notes},
        reason="Operator / Engineer acknowledgment of quality deviation",
        ip_address=get_client_ip(request),
    )
    return {"message": "Alert acknowledged successfully", "alert_id": alert.id}


@router.post("/{alert_id}/resolve", response_model=dict)
def resolve_alert(
    alert_id: int,
    action_in: AlertActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["quality_engineer", "quality_manager", "admin"])),
    request: Request = None,
):
    if not action_in.notes or not action_in.notes.strip():
        raise HTTPException(status_code=400, detail="Resolution notes/corrective actions are required to close an alert")

    existing = db.query(QualityAlert).filter(QualityAlert.id == alert_id).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Alert not found")
    old_status = existing.status

    try:
        alert = AlertEngine.resolve_alert(
            db,
            alert_id,
            current_user.id,
            notes=action_in.notes.strip(),
            expected_version=action_in.expected_version,
        )
    except ValueError as exc:
        if str(exc) == "VERSION_CONFLICT":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Alert was updated concurrently. Refresh and retry.")
        if str(exc) == "ALREADY_RESOLVED":
            raise HTTPException(status_code=400, detail="Alert is already resolved")
        raise

    log_audit(
        db,
        current_user,
        "RESOLVE",
        "QualityAlert",
        str(alert.id),
        old_value={"status": old_status},
        new_value={"status": "RESOLVED", "resolution": action_in.notes.strip()},
        reason="Quality engineer resolution and containment confirmation",
        ip_address=get_client_ip(request),
    )
    return {"message": "Alert resolved successfully", "alert_id": alert.id}
