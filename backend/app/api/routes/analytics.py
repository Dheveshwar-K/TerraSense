from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.alert import QualityAlert
from app.models.complaint import CustomerComplaint
from app.models.line import ProductionLine
from app.models.rejection import RejectionRecord
from app.models.sand_test import SandTestRecord
from app.models.user import User

router = APIRouter()


@router.get("/dashboard")
def get_dashboard_summary(
    line_code: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")
    seven_days_ago_str = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    fourteen_days_ago_str = (now - timedelta(days=14)).strftime("%Y-%m-%d")

    target_line = line_code.upper() if isinstance(line_code, str) and line_code and line_code.upper() != "ALL" else None

    # 1. Overall Sand Test Metrics
    today_q = db.query(func.count(SandTestRecord.id)).filter(SandTestRecord.test_date == today_str)
    week_q = db.query(
        func.count(SandTestRecord.id),
        func.sum(case((SandTestRecord.status == "CONFORMING", 1), else_=0)),
    ).filter(SandTestRecord.test_date >= seven_days_ago_str)

    if target_line:
        today_q = today_q.filter(SandTestRecord.line_code == target_line)
        week_q = week_q.filter(SandTestRecord.line_code == target_line)

    total_tests_today = today_q.scalar() or 0
    total_tests_week, conforming_tests_week = week_q.first()
    total_tests_week = int(total_tests_week or 0)
    conforming_tests_week = int(conforming_tests_week or 0)
    conforming_pct = round((conforming_tests_week / total_tests_week * 100.0), 1) if total_tests_week > 0 else 0.0

    alerts_q = db.query(func.count(QualityAlert.id)).filter(QualityAlert.status.in_(["OPEN", "ACKNOWLEDGED"]))
    if target_line:
        alerts_q = alerts_q.filter(QualityAlert.line_code == target_line)
    open_alerts_count = int(alerts_q.scalar() or 0)

    rej_q = db.query(
        func.sum(RejectionRecord.rejected_qty),
        func.sum(RejectionRecord.inspected_qty),
    ).filter(RejectionRecord.production_date >= seven_days_ago_str)
    if target_line:
        rej_q = rej_q.filter(RejectionRecord.line_code == target_line)
    rej_stats = rej_q.first()

    total_rejected = int(rej_stats[0] or 0)
    total_inspected = int(rej_stats[1] or 0)
    overall_rejection_rate = round((total_rejected / total_inspected * 100.0), 2) if total_inspected > 0 else 0.0

    comp_q = db.query(func.count(CustomerComplaint.id)).filter(CustomerComplaint.status != "CLOSED")
    if target_line:
        comp_q = comp_q.filter(CustomerComplaint.line_code == target_line)
    active_complaints = int(comp_q.scalar() or 0)

    # 2. Per-line aggregated stats in bulk (eliminates N+1 queries)
    active_lines = db.query(ProductionLine).filter(ProductionLine.is_active == True).order_by(ProductionLine.code.asc()).all()
    line_codes = [l.code for l in active_lines] or ["D1", "D2", "D3", "D4"]

    open_alert_rows = (
        db.query(QualityAlert.line_code, func.count(QualityAlert.id))
        .filter(QualityAlert.status == "OPEN")
        .group_by(QualityAlert.line_code)
        .all()
    )
    alerts_by_line = {lc: int(cnt) for lc, cnt in open_alert_rows}

    line_rej_rows = (
        db.query(
            RejectionRecord.line_code,
            func.sum(RejectionRecord.rejected_qty),
            func.sum(RejectionRecord.inspected_qty),
        )
        .filter(RejectionRecord.production_date >= seven_days_ago_str)
        .group_by(RejectionRecord.line_code)
        .all()
    )
    rej_by_line = {lc: (int(r or 0), int(i or 0)) for lc, r, i in line_rej_rows}

    lines_info = []
    for l_code in line_codes:
        latest_test = (
            db.query(SandTestRecord)
            .filter(SandTestRecord.line_code == l_code)
            .order_by(SandTestRecord.timestamp.desc(), SandTestRecord.id.desc())
            .first()
        )
        line_alerts = alerts_by_line.get(l_code, 0)
        l_rej, l_insp = rej_by_line.get(l_code, (0, 0))
        line_rej_rate = round((l_rej / l_insp * 100.0), 2) if l_insp > 0 else 0.0

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
            "molding_line": f"Disamatic {l_code}",
        })

    # 3. Rejection Trend by Line (Last 14 days)
    daily_rejections = (
        db.query(
            RejectionRecord.production_date,
            RejectionRecord.line_code,
            func.sum(RejectionRecord.rejected_qty).label("rej"),
            func.sum(RejectionRecord.inspected_qty).label("insp"),
        )
        .filter(RejectionRecord.production_date >= fourteen_days_ago_str)
        .group_by(RejectionRecord.production_date, RejectionRecord.line_code)
        .order_by(RejectionRecord.production_date.asc())
        .all()
    )

    trend_dict: dict[str, dict] = {}
    for d_date, d_line, d_rej, d_insp in daily_rejections:
        if d_date not in trend_dict:
            trend_dict[d_date] = {"date": d_date, "D1": 0.0, "D2": 0.0, "D3": 0.0, "D4": 0.0}
        rate = round((float(d_rej or 0) / float(d_insp) * 100.0), 2) if (d_insp or 0) > 0 else 0.0
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
            "active_complaints": active_complaints,
        },
        "lines": lines_info,
        "rejection_trends": rejection_trends,
    }
