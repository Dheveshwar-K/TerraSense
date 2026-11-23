from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.models.line import ProductionLine
from app.models.sand_test import SandTestRecord, SandTestValue
from app.models.rejection import RejectionRecord
from app.models.alert import QualityAlert
from app.models.complaint import CustomerComplaint
from app.models.user import User
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/dashboard")
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")
    seven_days_ago_str = (now - timedelta(days=7)).strftime("%Y-%m-%d")

    # 1. Overall Metrics
    total_tests_today = db.query(func.count(SandTestRecord.id)).filter(
        SandTestRecord.test_date == today_str
    ).scalar() or 0

    # If today has few tests, pull last 7 days metrics
    total_tests_week = db.query(func.count(SandTestRecord.id)).filter(
        SandTestRecord.test_date >= seven_days_ago_str
    ).scalar() or 0

    conforming_tests_week = db.query(func.count(SandTestRecord.id)).filter(
        SandTestRecord.test_date >= seven_days_ago_str,
        SandTestRecord.status == "CONFORMING"
    ).scalar() or 0

    conforming_pct = round((conforming_tests_week / total_tests_week * 100.0), 1) if total_tests_week > 0 else 100.0

    open_alerts_count = db.query(func.count(QualityAlert.id)).filter(
        QualityAlert.status.in_(["OPEN", "ACKNOWLEDGED"])
    ).scalar() or 0

    # Rejection totals in last 7 days
    rej_stats = db.query(
        func.sum(RejectionRecord.rejected_qty),
        func.sum(RejectionRecord.inspected_qty)
    ).filter(RejectionRecord.production_date >= seven_days_ago_str).first()

    total_rejected = rej_stats[0] or 0
    total_inspected = rej_stats[1] or 0
    overall_rejection_rate = round((total_rejected / total_inspected * 100.0), 2) if total_inspected > 0 else 0.0

    active_complaints = db.query(func.count(CustomerComplaint.id)).filter(
        CustomerComplaint.status != "CLOSED"
    ).scalar() or 0

    # 2. Production Line Cards (D1, D2, D3, D4)
    lines_info = []
    for l_code in ["D1", "D2", "D3", "D4"]:
        # Latest test
        latest_test = db.query(SandTestRecord).filter(
            SandTestRecord.line_code == l_code
        ).order_by(SandTestRecord.timestamp.desc()).first()

        # Open alerts for line
        line_alerts = db.query(QualityAlert).filter(
            QualityAlert.line_code == l_code,
            QualityAlert.status == "OPEN"
        ).count()

        # Rejection stats for line in last 7 days
        line_rej = db.query(
            func.sum(RejectionRecord.rejected_qty),
            func.sum(RejectionRecord.inspected_qty)
        ).filter(
            RejectionRecord.line_code == l_code,
            RejectionRecord.production_date >= seven_days_ago_str
        ).first()

        line_rej_rate = round(((line_rej[0] or 0) / (line_rej[1] or 1) * 100.0), 2) if (line_rej[1] or 0) > 0 else 0.0

        # Health status determination
        if line_alerts > 0 or (latest_test and latest_test.status == "OUT_OF_SPEC"):
            health = "CRITICAL"
        elif latest_test and latest_test.status == "WARNING":
            health = "WARNING"
        else:
            health = "HEALTHY"

        lines_info.append({
            "line_code": l_code,
            "health": health,
            "latest_test_number": latest_test.test_number if latest_test else "No tests",
            "latest_test_status": latest_test.status if latest_test else "UNKNOWN",
            "latest_test_time": latest_test.timestamp.isoformat() if latest_test else None,
            "open_alerts": line_alerts,
            "rejection_rate": line_rej_rate,
            "molding_line": f"Disamatic {l_code}"
        })

    # 3. Rejection Trend by Line (Last 14 days)
    fourteen_days_ago = (now - timedelta(days=14)).strftime("%Y-%m-%d")
    daily_rejections = db.query(
        RejectionRecord.production_date,
        RejectionRecord.line_code,
        func.sum(RejectionRecord.rejected_qty).label("rej"),
        func.sum(RejectionRecord.inspected_qty).label("insp")
    ).filter(RejectionRecord.production_date >= fourteen_days_ago).group_by(
        RejectionRecord.production_date, RejectionRecord.line_code
    ).order_by(RejectionRecord.production_date.asc()).all()

    # Format into dates
    trend_dict = {}
    for d_date, d_line, d_rej, d_insp in daily_rejections:
        if d_date not in trend_dict:
            trend_dict[d_date] = {"date": d_date, "D1": 0.0, "D2": 0.0, "D3": 0.0, "D4": 0.0}
        rate = round((d_rej / d_insp * 100.0), 2) if d_insp > 0 else 0.0
        trend_dict[d_date][d_line] = rate

    rejection_trends = sorted(list(trend_dict.values()), key=lambda x: x["date"])

    return {
        "metrics": {
            "total_tests_today": total_tests_today,
            "total_tests_week": total_tests_week,
            "conforming_percentage": conforming_pct,
            "open_alerts": open_alerts_count,
            "total_rejected_qty": total_rejected,
            "total_inspected_qty": total_inspected,
            "overall_rejection_rate": overall_rejection_rate,
            "active_complaints": active_complaints
        },
        "lines": lines_info,
        "rejection_trends": rejection_trends
    }
