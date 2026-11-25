import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.alert import QualityAlert
from app.models.sand_test import SandTestRecord, SandTestValue
from app.services.spc_engine import D2_MR2, SPCEngine


class AlertEngine:
    """
    Quality Alert Engine.
    Evaluates parameter specifications and statistical Nelson rule violations,
    deduplicating active alerts and handling optimistic concurrency.
    """

    @staticmethod
    def process_sand_test_record(db: Session, record: SandTestRecord) -> list[QualityAlert]:
        generated_alerts: list[QualityAlert] = []
        now = datetime.now(timezone.utc)

        for val in record.values:
            param = val.parameter
            if not param or not param.is_active:
                continue

            # 1. Engineering Specification Limits (LSL / USL)
            spec_violated = False
            severity = "WARNING"
            desc = ""

            if param.usl is not None and val.measured_value > param.usl:
                spec_violated = True
                severity = "CRITICAL"
                desc = (
                    f"Parameter {param.name} ({param.code}) on Line {record.line_code} measured "
                    f"{val.measured_value:.2f} {val.unit}, exceeding USL ({param.usl:.2f} {val.unit})."
                )
            elif param.lsl is not None and val.measured_value < param.lsl:
                spec_violated = True
                severity = "CRITICAL"
                desc = (
                    f"Parameter {param.name} ({param.code}) on Line {record.line_code} measured "
                    f"{val.measured_value:.2f} {val.unit}, below LSL ({param.lsl:.2f} {val.unit})."
                )

            if spec_violated:
                existing = (
                    db.query(QualityAlert)
                    .filter(
                        QualityAlert.line_code == record.line_code,
                        QualityAlert.parameter_id == param.id,
                        QualityAlert.status.in_(["OPEN", "ACKNOWLEDGED"]),
                        QualityAlert.alert_type == "SPEC_VIOLATION",
                    )
                    .first()
                )
                if not existing:
                    suffix = uuid.uuid4().hex[:6].upper()
                    alert_code = f"ALT-SPEC-{record.line_code}-{param.code}-{now.strftime('%y%m%d%H%M%S')}-{suffix}"
                    alert = QualityAlert(
                        alert_code=alert_code,
                        line_code=record.line_code,
                        parameter_id=param.id,
                        record_id=record.id,
                        alert_type="SPEC_VIOLATION",
                        severity=severity,
                        description=desc,
                        status="OPEN",
                        timestamp=now,
                    )
                    db.add(alert)
                    generated_alerts.append(alert)

            # 2. Statistical Process Control (SPC) Nelson Rule Violations
            recent_vals = (
                db.query(SandTestValue.measured_value)
                .join(SandTestRecord)
                .filter(
                    SandTestRecord.line_code == record.line_code,
                    SandTestValue.parameter_id == param.id,
                )
                .order_by(SandTestRecord.timestamp.desc(), SandTestRecord.id.desc())
                .limit(30)
                .all()
            )

            if len(recent_vals) >= 6:
                arr = [v[0] for v in reversed(recent_vals)]
                mean_x = float(sum(arr)) / len(arr)
                diffs = [abs(arr[k] - arr[k - 1]) for k in range(1, len(arr))]
                mean_mr = float(sum(diffs)) / len(diffs) if diffs else 0.0
                sigma = mean_mr / D2_MR2

                if sigma > 0:
                    violations = SPCEngine.evaluate_nelson_rules(arr, mean_x, sigma)
                    latest_violations = [v for v in violations if v["index"] == len(arr) - 1]
                    for v in latest_violations:
                        existing_rule_alert = (
                            db.query(QualityAlert)
                            .filter(
                                QualityAlert.line_code == record.line_code,
                                QualityAlert.parameter_id == param.id,
                                QualityAlert.nelson_rule_triggered == v["rule_name"],
                                QualityAlert.status.in_(["OPEN", "ACKNOWLEDGED"]),
                            )
                            .first()
                        )
                        if not existing_rule_alert:
                            suffix = uuid.uuid4().hex[:6].upper()
                            alert_code = f"ALT-SPC-{record.line_code}-{param.code}-{now.strftime('%y%m%d%H%M%S')}-{suffix}"
                            rule_desc = f"{v['rule_name']}: {v['description']} on Line {record.line_code} for {param.name}."
                            alert = QualityAlert(
                                alert_code=alert_code,
                                line_code=record.line_code,
                                parameter_id=param.id,
                                record_id=record.id,
                                alert_type="SPC_RULE_VIOLATION",
                                severity="WARNING",
                                description=rule_desc,
                                nelson_rule_triggered=v["rule_name"],
                                status="OPEN",
                                timestamp=now,
                            )
                            db.add(alert)
                            generated_alerts.append(alert)

        db.commit()
        return generated_alerts

    @staticmethod
    def acknowledge_alert(
        db: Session,
        alert_id: int,
        user_id: int,
        notes: Optional[str] = None,
        expected_version: Optional[int] = None,
    ) -> Optional[QualityAlert]:
        alert = db.query(QualityAlert).filter(QualityAlert.id == alert_id).first()
        if not alert:
            return None
        if expected_version is not None and alert.version != expected_version:
            raise ValueError("VERSION_CONFLICT")
        if alert.status == "RESOLVED":
            raise ValueError("ALREADY_RESOLVED")

        alert.status = "ACKNOWLEDGED"
        alert.acknowledged_by_id = user_id
        alert.acknowledged_at = datetime.now(timezone.utc)
        alert.version = (alert.version or 1) + 1
        if notes:
            alert.resolution_notes = (alert.resolution_notes or "") + f"\n[Ack Notes]: {notes}"
        db.commit()
        db.refresh(alert)
        return alert

    @staticmethod
    def resolve_alert(
        db: Session,
        alert_id: int,
        user_id: int,
        notes: str,
        expected_version: Optional[int] = None,
    ) -> Optional[QualityAlert]:
        alert = db.query(QualityAlert).filter(QualityAlert.id == alert_id).first()
        if not alert:
            return None
        if expected_version is not None and alert.version != expected_version:
            raise ValueError("VERSION_CONFLICT")
        if alert.status == "RESOLVED":
            raise ValueError("ALREADY_RESOLVED")

        alert.status = "RESOLVED"
        alert.resolved_by_id = user_id
        alert.resolved_at = datetime.now(timezone.utc)
        alert.version = (alert.version or 1) + 1
        alert.resolution_notes = (alert.resolution_notes or "") + f"\n[Resolution]: {notes}"
        db.commit()
        db.refresh(alert)
        return alert
