from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_client_ip, log_audit, require_role
from app.core.config import settings
from app.core.database import get_db
from app.models.audit import AuditLog
from app.models.complaint import CustomerComplaint
from app.models.rejection import RejectionRecord
from app.models.sand_test import SandTestRecord
from app.models.user import User
from app.services.report_generator import ReportGenerator

router = APIRouter()


@router.get("/export")
def export_report(
    report_type: str = Query("SAND_TEST_SHEET", description="SAND_TEST_SHEET, REJECTION_PARETO, AUDIT_TRAIL, COMPLAINTS"),
    format: str = Query("pdf", description="pdf, excel, csv"),
    line_code: str = Query("ALL"),
    start_date: str = None,
    end_date: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["quality_engineer", "supervisor", "quality_manager", "admin"])),
    request: Request = None,
):
    now_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    norm_line = line_code.upper() if line_code else "ALL"

    if report_type == "SAND_TEST_SHEET":
        query = db.query(SandTestRecord).options(joinedload(SandTestRecord.operator))
        if norm_line != "ALL":
            query = query.filter(SandTestRecord.line_code == norm_line)
        if start_date:
            query = query.filter(SandTestRecord.test_date >= start_date)
        if end_date:
            query = query.filter(SandTestRecord.test_date <= end_date)
        records = query.order_by(SandTestRecord.timestamp.desc()).limit(200).all()

        headers = ["Test No", "Line", "Date", "Shift", "Hour", "Status", "Operator"]
        rows = [
            [
                r.test_number,
                r.line_code,
                r.test_date,
                f"S{r.shift}",
                f"{r.test_hour}:00",
                r.status,
                r.operator.full_name if r.operator else "N/A",
            ]
            for r in records
        ]
        title = f"Foundry Sand Testing Log ({norm_line})"
        subtitle = "Comprehensive Physical & Chemical Sand Verification History"
        filename = f"Sand_Test_Report_{norm_line}_{now_str}"

    elif report_type == "REJECTION_PARETO":
        query = db.query(RejectionRecord).options(
            joinedload(RejectionRecord.product),
            joinedload(RejectionRecord.defect_category),
        )
        if norm_line != "ALL":
            query = query.filter(RejectionRecord.line_code == norm_line)
        if start_date:
            query = query.filter(RejectionRecord.production_date >= start_date)
        if end_date:
            query = query.filter(RejectionRecord.production_date <= end_date)
        records = query.order_by(RejectionRecord.production_date.desc()).limit(200).all()

        headers = ["Rejection No", "Line", "Date", "Shift", "Product", "Defect", "Rejected", "Inspected", "Scrap %"]
        rows = [
            [
                r.rejection_number,
                r.line_code,
                r.production_date,
                f"S{r.shift}",
                r.product.part_name if r.product else "N/A",
                r.defect_category.name if r.defect_category else "N/A",
                r.rejected_qty,
                r.inspected_qty,
                f"{r.rejection_rate:.2f}%",
            ]
            for r in records
        ]
        title = f"Casting Rejection & Defect Report ({norm_line})"
        subtitle = "Defect Log and Scrap Analytics for Quality 4.0 Foundry"
        filename = f"Rejection_Report_{norm_line}_{now_str}"

    elif report_type == "AUDIT_TRAIL":
        query = db.query(AuditLog)
        if start_date:
            query = query.filter(AuditLog.timestamp >= datetime.strptime(start_date, "%Y-%m-%d"))
        if end_date:
            query = query.filter(AuditLog.timestamp < datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1))
        records = query.order_by(AuditLog.sequence_no.desc(), AuditLog.timestamp.desc()).limit(200).all()

        headers = ["Seq", "Timestamp (UTC)", "Actor", "Role", "Action", "Entity", "Entity ID", "Outcome", "Reason"]
        rows = [
            [
                a.sequence_no or a.id,
                a.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                a.user_name,
                a.user_role,
                a.action,
                a.entity_type,
                a.entity_id or "",
                a.outcome or "SUCCESS",
                a.reason or "",
            ]
            for a in records
        ]
        title = "IATF 16949 Digital Audit Trail"
        subtitle = "Hash-Chained Quality Event and Data Modification Log"
        filename = f"Audit_Trail_{now_str}"

    elif report_type == "COMPLAINTS":
        query = db.query(CustomerComplaint).options(
            joinedload(CustomerComplaint.product),
            joinedload(CustomerComplaint.defect_category),
        )
        if norm_line != "ALL":
            query = query.filter(CustomerComplaint.line_code == norm_line)
        records = query.order_by(CustomerComplaint.created_at.desc()).all()

        headers = ["Complaint No", "Customer", "Date", "Product", "Defect", "Qty", "Severity", "Status"]
        rows = [
            [
                c.complaint_number,
                c.customer_name,
                c.received_date,
                c.product.part_name if c.product else "N/A",
                c.defect_category.name if c.defect_category else "N/A",
                c.affected_qty,
                c.severity,
                c.status,
            ]
            for c in records
        ]
        title = "Customer Quality Complaints & 8D CAPA Log"
        subtitle = "Customer Feedback and Corrective Action Verification"
        filename = f"Complaints_Report_{now_str}"

    else:
        raise HTTPException(status_code=400, detail="Unsupported report type")

    fmt = format.lower()
    if fmt not in ("csv", "excel", "xlsx", "pdf"):
        raise HTTPException(status_code=400, detail="Format must be 'pdf', 'excel', or 'csv'")

    log_audit(
        db,
        current_user,
        "EXPORT",
        "Report",
        report_type,
        new_value={"format": fmt, "line_code": norm_line, "rows": len(rows)},
        reason=f"Generated {fmt.upper()} report for {report_type}",
        ip_address=get_client_ip(request),
    )

    if fmt == "csv":
        data = ReportGenerator.generate_csv(headers, rows, title=title)
        return Response(
            content=data,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}.csv"},
        )

    if fmt in ("excel", "xlsx"):
        sheets_data = [{"title": title[:30], "headers": headers, "rows": rows}]
        data = ReportGenerator.generate_excel(sheets_data, title=title)
        return Response(
            content=data,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}.xlsx"},
        )

    metadata = {
        "Facility": "Quality 4.0 Foundry Plant",
        "Molding Lines": norm_line if norm_line != "ALL" else "D1, D2, D3, D4",
        "Generated By": current_user.full_name,
        "User Role": current_user.role,
        "Standard": "IATF 16949 / ISO 9001",
        "Report Type": report_type,
    }
    kpis = {
        "Total Records": str(len(rows)),
        "Status": "CONFIDENTIAL / AUDIT READY",
        "Environment": settings.ENVIRONMENT.upper(),
    }
    pdf_bytes = ReportGenerator.generate_pdf(title, subtitle, metadata, headers, rows, summary_kpis=kpis)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}.pdf"},
    )
