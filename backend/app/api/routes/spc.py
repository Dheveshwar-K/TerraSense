from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.parameter import Parameter
from app.models.sand_test import SandTestRecord, SandTestValue
from app.models.rejection import RejectionRecord
from app.models.user import User
from app.services.spc_engine import SPCEngine
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/imr")
def get_imr_chart(
    line_code: str = Query(..., description="Line code (D1, D2, D3, D4)"),
    parameter_code: str = Query(..., description="Parameter code (e.g. MOISTURE, COMPACT, GCS, PERM)"),
    start_date: str = None,
    end_date: str = None,
    shift: int = None,
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    param = db.query(Parameter).filter(Parameter.code == parameter_code.upper()).first()
    if not param:
        raise HTTPException(status_code=404, detail="Parameter not found")

    query = db.query(SandTestValue.measured_value, SandTestRecord.timestamp, SandTestRecord.test_number).join(SandTestRecord).filter(
        SandTestRecord.line_code == line_code.upper(),
        SandTestValue.parameter_id == param.id
    )
    if start_date:
        query = query.filter(SandTestRecord.test_date >= start_date)
    if end_date:
        query = query.filter(SandTestRecord.test_date <= end_date)
    if shift:
        query = query.filter(SandTestRecord.shift == shift)

    limit = limit if isinstance(limit, int) else 100
    # Order chronologically for moving range and Nelson sequence analysis
    results = query.order_by(SandTestRecord.timestamp.asc()).limit(limit).all()

    if not results or len(results) < 2:
        return {
            "parameter_name": param.name,
            "parameter_code": param.code,
            "unit": param.unit,
            "line_code": line_code.upper(),
            "target": param.target_value,
            "lsl": param.lsl,
            "usl": param.usl,
            "message": "Insufficient data points for SPC calculation (minimum 2 required)",
            "sample_size": len(results),
            "points": []
        }

    vals = [r[0] for r in results]
    timestamps = [r[1].strftime("%d-%b %H:%M") if r[1] else r[2] for r in results]

    chart = SPCEngine.calculate_imr(vals, timestamps, lsl=param.lsl, usl=param.usl)
    chart.update({
        "parameter_name": param.name,
        "parameter_code": param.code,
        "unit": param.unit,
        "line_code": line_code.upper(),
        "target": param.target_value,
        "lsl": param.lsl,
        "usl": param.usl
    })
    return chart

@router.get("/xbar-r")
def get_xbar_r_chart(
    line_code: str = Query(...),
    parameter_code: str = Query(...),
    start_date: str = None,
    end_date: str = None,
    subgroup_by: str = Query("shift", description="'shift' or 'date'"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    param = db.query(Parameter).filter(Parameter.code == parameter_code.upper()).first()
    if not param:
        raise HTTPException(status_code=404, detail="Parameter not found")

    query = db.query(SandTestValue.measured_value, SandTestRecord.test_date, SandTestRecord.shift).join(SandTestRecord).filter(
        SandTestRecord.line_code == line_code.upper(),
        SandTestValue.parameter_id == param.id
    )
    if start_date:
        query = query.filter(SandTestRecord.test_date >= start_date)
    if end_date:
        query = query.filter(SandTestRecord.test_date <= end_date)

    rows = query.order_by(SandTestRecord.timestamp.asc()).all()
    if not rows:
        return {"error": "No data found for selection", "points": []}

    # Group into subgroups
    subgroup_dict = {}
    for val, t_date, t_shift in rows:
        key = f"{t_date} S{t_shift}" if subgroup_by == "shift" else t_date
        if key not in subgroup_dict:
            subgroup_dict[key] = []
        subgroup_dict[key].append(val)

    # Filter subgroups with at least 2 samples
    subgroups = []
    labels = []
    for k, v in list(subgroup_dict.items())[-30:]:  # Last 30 subgroups
        if len(v) >= 2:
            subgroups.append(v)
            labels.append(k)

    res = SPCEngine.calculate_xbar_r(subgroups, labels)
    res.update({
        "parameter_name": param.name,
        "parameter_code": param.code,
        "unit": param.unit,
        "line_code": line_code.upper(),
        "lsl": param.lsl,
        "usl": param.usl,
        "target": param.target_value
    })
    return res

@router.get("/p-chart")
def get_p_chart(
    line_code: str = Query("ALL"),
    start_date: str = None,
    end_date: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(RejectionRecord)
    if line_code and line_code != "ALL":
        query = query.filter(RejectionRecord.line_code == line_code.upper())
    if start_date:
        query = query.filter(RejectionRecord.production_date >= start_date)
    if end_date:
        query = query.filter(RejectionRecord.production_date <= end_date)

    records = query.order_by(RejectionRecord.production_date.asc(), RejectionRecord.shift.asc()).limit(50).all()
    if not records:
        return {"error": "No rejection records for P-chart", "points": []}

    defective = [r.rejected_qty for r in records]
    inspected = [r.inspected_qty for r in records]
    labels = [f"{r.line_code}-{r.production_date[5:]}-S{r.shift}" for r in records]

    return SPCEngine.calculate_p_chart(defective, inspected, labels)

@router.get("/capability")
def get_process_capability(
    line_code: str = Query(...),
    parameter_code: str = Query(...),
    start_date: str = None,
    end_date: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    param = db.query(Parameter).filter(Parameter.code == parameter_code.upper()).first()
    if not param:
        raise HTTPException(status_code=404, detail="Parameter not found")

    query = db.query(SandTestValue.measured_value).join(SandTestRecord).filter(
        SandTestRecord.line_code == line_code.upper(),
        SandTestValue.parameter_id == param.id
    )
    if start_date:
        query = query.filter(SandTestRecord.test_date >= start_date)
    if end_date:
        query = query.filter(SandTestRecord.test_date <= end_date)

    results = query.order_by(SandTestRecord.timestamp.asc()).all()
    vals = [r[0] for r in results]

    cap = SPCEngine.calculate_capability(vals, lsl=param.lsl, usl=param.usl, target=param.target_value)
    cap.update({
        "parameter_name": param.name,
        "parameter_code": param.code,
        "unit": param.unit,
        "line_code": line_code.upper()
    })
    return cap
