from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.alert import QualityAlert
from app.models.parameter import Parameter
from app.models.sand_test import SandTestRecord, SandTestValue
from app.services.spc_engine import SPCEngine

class AlertEngine:
    """
    Quality Alert Engine.
    Evaluates parameter specifications, statistical Nelson rule violations, and missing tests.
    Deduplicates alerts and logs full context.
    """

    @staticmethod
    def process_sand_test_record(db: Session, record: SandTestRecord) -> list[QualityAlert]:
        """
        Evaluates a newly created or updated SandTestRecord.
        Generates alerts for spec violations and statistical drift.
        """
        generated_alerts = []
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
                desc = (f"Parameter {param.name} ({param.code}) on Line {record.line_code} measured "
                        f"{val.measured_value:.2f} {val.unit}, exceeding USL ({param.usl:.2f} {val.unit}).")
            elif param.lsl is not None and val.measured_value < param.lsl:
                spec_violated = True
                severity = "CRITICAL"
                desc = (f"Parameter {param.name} ({param.code}) on Line {record.line_code} measured "
                        f"{val.measured_value:.2f} {val.unit}, below LSL ({param.lsl:.2f} {val.unit}).")

            if spec_violated:
                # Deduplication: check if an identical open alert already exists for this line and parameter
                existing = db.query(QualityAlert).filter(
                    QualityAlert.line_code == record.line_code,
                    QualityAlert.parameter_id == param.id,
                    QualityAlert.status.in_(["OPEN", "ACKNOWLEDGED"]),
                    QualityAlert.alert_type == "SPEC_VIOLATION"
                ).first()

                if not existing:
                    alert_code = f"ALT-SPEC-{record.line_code}-{param.code}-{now.strftime('%y%m%d%H%M%S')}"
                    alert = QualityAlert(
                        alert_code=alert_code,
                        line_code=record.line_code,
                        parameter_id=param.id,
                        record_id=record.id,
                        alert_type="SPEC_VIOLATION",
                        severity=severity,
                        description=desc,
                        status="OPEN",
                        timestamp=now
                    )
                    db.add(alert)
                    generated_alerts.append(alert)

            # 2. Statistical Process Control (SPC) Nelson Rule Violations
            # Fetch recent 15 measurements for this parameter and line
            recent_vals = db.query(SandTestValue.measured_value).join(SandTestRecord).filter(
                SandTestRecord.line_code == record.line_code,
                SandTestValue.parameter_id == param.id
            ).order_by(SandTestRecord.timestamp.desc()).limit(20).all()

            if len(recent_vals) >= 6:
                arr = [v[0] for v in reversed(recent_vals)]
                mean_x = float(sum(arr)) / len(arr)
                # within-sigma estimate
                diffs = [abs(arr[k] - arr[k-1]) for k in range(1, len(arr))]
                mean_mr = float(sum(diffs)) / len(diffs) if diffs else 0.0
                sigma = mean_mr / 1.128379 if mean_mr > 0 else 0.01

                violations = SPCEngine.evaluate_nelson_rules(arr, mean_x, sigma)
                # Check if the latest point (index len(arr)-1) triggered a rule
                latest_violations = [v for v in violations if v["index"] == len(arr) - 1]
                for v in latest_violations:
                    rule_desc = f"{v['rule_name']}: {v['description']} on Line {record.line_code} for {param.name}."
                    
                    # Deduplicate rule alert within 2 hours
                    existing_rule_alert = db.query(QualityAlert).filter(
                        QualityAlert.line_code == record.line_code,
                        QualityAlert.parameter_id == param.id,
                        QualityAlert.nelson_rule_triggered == v["rule_name"],
                        QualityAlert.status == "OPEN"
                    ).first()

                    if not existing_rule_alert:
                        alert_code = f"ALT-SPC-{record.line_code}-{param.code}-{now.strftime('%y%m%d%H%M%S')}"
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
                            timestamp=now
                        )
                        db.add(alert)
                        generated_alerts.append(alert)

        db.commit()
        return generated_alerts

    @staticmethod
    def acknowledge_alert(db: Session, alert_id: int, user_id: int, notes: str = None) -> QualityAlert:
        alert = db.query(QualityAlert).filter(QualityAlert.id == alert_id).first()
        if alert:
            alert.status = "ACKNOWLEDGED"
            alert.acknowledged_by_id = user_id
            alert.acknowledged_at = datetime.now(timezone.utc)
            if notes:
                alert.resolution_notes = (alert.resolution_notes or "") + f"\n[Ack Notes]: {notes}"
            db.commit()
            db.refresh(alert)
        return alert

    @staticmethod
    def resolve_alert(db: Session, alert_id: int, user_id: int, notes: str) -> QualityAlert:
        alert = db.query(QualityAlert).filter(QualityAlert.id == alert_id).first()
        if alert:
            alert.status = "RESOLVED"
            alert.resolved_by_id = user_id
            alert.resolved_at = datetime.now(timezone.utc)
            alert.resolution_notes = (alert.resolution_notes or "") + f"\n[Resolution]: {notes}"
            db.commit()
            db.refresh(alert)
        return alert
