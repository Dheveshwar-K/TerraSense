from typing import Optional
from pydantic import BaseModel

class ReportRequest(BaseModel):
    report_type: str  # SAND_TEST_SHEET, SPC_SUMMARY, REJECTION_PARETO, AUDIT_TRAIL, COMPLAINTS
    format: str = "pdf"  # pdf, excel, csv
    line_code: Optional[str] = "ALL"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    shift: Optional[int] = None
    parameter_code: Optional[str] = None
