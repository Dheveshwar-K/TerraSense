from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.alert import QualityAlert
from app.models.user import User
from app.schemas.alert import AlertResponse, AlertActionRequest
from app.api.deps import get_current_user, require_role, log_audit
from app.services.alert_engine import AlertEngine

router = APIRouter()

@router.get("", response_model=list[AlertResponse])
def list_alerts(
    line_code: str = None,
    status: str = None,
    severity: str = None,
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(QualityAlert)
    if line_code and line_code != "ALL":
        query = query.filter(QualityAlert.line_code == line_code.upper())
    if status and status != "ALL":
        query = query.filter(QualityAlert.status == status.upper())
    if severity and severity != "ALL":
        query = query.filter(QualityAlert.severity == severity.upper())

    limit = limit if isinstance(limit, int) else 100
    records = query.order_by(QualityAlert.timestamp.desc()).limit(limit).all()

    res = []
    for a in records:
        res.append(AlertResponse(
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
            timestamp=a.timestamp,
            acknowledged_by_name=a.acknowledged_by.full_name if a.acknowledged_by else None,
            resolved_by_name=a.resolved_by.full_name if a.resolved_by else None,
            resolution_notes=a.resolution_notes
        ))
    return res

@router.post("/{alert_id}/acknowledge", response_model=dict)
def acknowledge_alert(
    alert_id: int,
    action_in: AlertActionRequest = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    notes = action_in.notes if action_in else None
    alert = AlertEngine.acknowledge_alert(db, alert_id, current_user.id, notes=notes)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    log_audit(
        db, current_user, "ACKNOWLEDGE", "QualityAlert", str(alert.id),
        old_value={"status": "OPEN"},
        new_value={"status": "ACKNOWLEDGED", "notes": notes},
        reason="Operator / Engineer acknowledgment of quality deviation"
    )
    return {"message": "Alert acknowledged successfully", "alert_id": alert.id}

@router.post("/{alert_id}/resolve", response_model=dict)
def resolve_alert(
    alert_id: int,
    action_in: AlertActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["quality_engineer", "quality_manager", "admin"]))
):
    if not action_in.notes:
        raise HTTPException(status_code=400, detail="Resolution notes/corrective actions are required to close an alert")

    alert = AlertEngine.resolve_alert(db, alert_id, current_user.id, notes=action_in.notes)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    log_audit(
        db, current_user, "RESOLVE", "QualityAlert", str(alert.id),
        old_value={"status": "ACKNOWLEDGED"},
        new_value={"status": "RESOLVED", "resolution": action_in.notes},
        reason="Quality engineer resolution and containment confirmation"
    )
    return {"message": "Alert resolved successfully", "alert_id": alert.id}
