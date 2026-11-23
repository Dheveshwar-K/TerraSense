from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.sand_test import SandTestRecord, SandTestValue
from app.models.rejection import RejectionRecord
from app.models.complaint import CustomerComplaint
from app.models.audit import AuditLog
from app.models.user import User
from app.services.report_generator import ReportGenerator
from app.api.deps import get_current_user, log_audit

router = APIRouter()

@router.get("/export")
def export_report(
    report_type: str = Query("SAND_TEST_SHEET", description="SAND_TEST_SHEET, SPC_SUMMARY, REJECTION_PARETO, AUDIT_TRAIL, COMPLAINTS"),
    format: str = Query("pdf", description="pdf, excel, csv"),
    line_code: str = Query("ALL"),
    start_date: str = None,
    end_date: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    now_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_audit(db, current_user, "EXPORT", "Report", report_type, reason=f"Generated {format.upper()} report for {report_type}")

    if report_type == "SAND_TEST_SHEET":
        query = db.query(SandTestRecord)
        if line_code != "ALL":
            query = query.filter(SandTestRecord.line_code == line_code.upper())
        if start_date:
            query = query.filter(SandTestRecord.test_date >= start_date)
        if end_date:
            query = query.filter(SandTestRecord.test_date <= end_date)
        records = query.order_by(SandTestRecord.timestamp.desc()).limit(100).all()

        headers = ["Test No", "Line", "Date", "Shift", "Hour", "Status", "Operator"]
        rows = []
        for r in records:
            rows.append([
                r.test_number,
                r.line_code,
                r.test_date,
                f"S{r.shift}",
                f"{r.test_hour}:00",
                r.status,
                r.operator.full_name if r.operator else "N/A"
            ])

        title = f"Foundry Sand Testing Log ({line_code})"
        subtitle = "Comprehensive Physical & Chemical Sand Verification History"
        filename = f"Sand_Test_Report_{line_code}_{now_str}"

    elif report_type == "REJECTION_PARETO":
        query = db.query(RejectionRecord)
        if line_code != "ALL":
            query = query.filter(RejectionRecord.line_code == line_code.upper())
        records = query.order_by(RejectionRecord.production_date.desc()).limit(100).all()

        headers = ["Rejection No", "Line", "Date", "Shift", "Product", "Defect", "Rejected", "Inspected", "Scrap %"]
        rows = []
        for r in records:
            rows.append([
                r.rejection_number,
                r.line_code,
                r.production_date,
                f"S{r.shift}",
                r.product.part_name if r.product else "N/A",
                r.defect_category.name if r.defect_category else "N/A",
                r.rejected_qty,
                r.inspected_qty,
                f"{r.rejection_rate:.2f}%"
            ])

        title = f"Casting Rejection & Defect Report ({line_code})"
        subtitle = "Defect Log and Scrap Analytics for Quality 4.0 Foundry"
        filename = f"Rejection_Report_{line_code}_{now_str}"

    elif report_type == "AUDIT_TRAIL":
        records = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(150).all()
        headers = ["Timestamp (UTC)", "Actor", "Role", "Action", "Entity", "Entity ID", "Reason"]
        rows = []
        for a in records:
            rows.append([
                a.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                a.user_name,
                a.user_role,
                a.action,
                a.entity_type,
                a.entity_id or "",
                a.reason or ""
            ])

        title = "IATF 16949 Digital Audit Trail"
        subtitle = "Immutable Quality Event and Data Modification Log"
        filename = f"Audit_Trail_{now_str}"

    elif report_type == "COMPLAINTS":
        records = db.query(CustomerComplaint).order_by(CustomerComplaint.created_at.desc()).all()
        headers = ["Complaint No", "Customer", "Date", "Product", "Defect", "Qty", "Severity", "Status"]
        rows = []
        for c in records:
            rows.append([
                c.complaint_number,
                c.customer_name,
                c.received_date,
                c.product.part_name if c.product else "N/A",
                c.defect_category.name if c.defect_category else "N/A",
                c.affected_qty,
                c.severity,
                c.status
            ])

        title = "Customer Quality Complaints & 8D CAPA Log"
        subtitle = "Customer Feedback and Corrective Action Verification"
        filename = f"Complaints_Report_{now_str}"

    else:
        raise HTTPException(status_code=400, detail="Unsupported report type")

    # Render according to requested format
    if format.lower() == "csv":
        data = ReportGenerator.generate_csv(headers, rows, title=title)
        return Response(
            content=data,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}.csv"}
        )

    elif format.lower() == "excel" or format.lower() == "xlsx":
        sheets_data = [{"title": title[:30], "headers": headers, "rows": rows}]
        data = ReportGenerator.generate_excel(sheets_data, title=title)
        return Response(
            content=data,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}.xlsx"}
        )

    elif format.lower() == "pdf":
        metadata = {
            "Facility": "Quality 4.0 Foundry Plant",
            "Molding Lines": line_code if line_code != "ALL" else "D1, D2, D3, D4",
            "Generated By": current_user.full_name,
            "User Role": current_user.role,
            "Standard": "IATF 16949 / ISO 9001",
            "Report Type": report_type
        }
        kpis = {
            "Total Records": str(len(rows)),
            "Status": "CONFIDENTIAL / AUDIT READY",
            "Environment": "Production"
        }
        pdf_bytes = ReportGenerator.generate_pdf(title, subtitle, metadata, headers, rows, summary_kpis=kpis)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}.pdf"}
        )

    else:
        raise HTTPException(status_code=400, detail="Format must be 'pdf', 'excel', or 'csv'")
