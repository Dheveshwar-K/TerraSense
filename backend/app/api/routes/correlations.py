from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.parameter import Parameter
from app.models.rejection import DefectCategory, RejectionRecord
from app.models.sand_test import SandTestRecord, SandTestValue
from app.models.user import User
from app.services.correlation_engine import CorrelationEngine
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/pair")
def analyze_correlation_pair(
    line_code: str = Query("D2", description="Production Line (D1, D2, D3, D4)"),
    parameter_code: str = Query("MOISTURE", description="Parameter Code (MOISTURE, COMPACT, GCS, PERM)"),
    defect_code: str = Query("POROSITY", description="Defect Code (POROSITY, BLOWHOLE, SAND_INCLUSION)"),
    lag_hours: int = Query(12, description="Process lag hours (0, 6, 12, 24, 48, 72)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    param = db.query(Parameter).filter(Parameter.code == parameter_code.upper()).first()
    if not param:
        raise HTTPException(status_code=404, detail="Parameter not found")

    defect = db.query(DefectCategory).filter(DefectCategory.code == defect_code.upper()).first()
    if not defect:
        raise HTTPException(status_code=404, detail="Defect category not found")

    # Fetch sand points
    sand_rows = db.query(
        SandTestValue.measured_value,
        SandTestRecord.timestamp,
        SandTestValue.status
    ).join(SandTestRecord).filter(
        SandTestRecord.line_code == line_code.upper(),
        SandTestValue.parameter_id == param.id
    ).order_by(SandTestRecord.timestamp.asc()).all()

    sand_points = [
        {"value": r[0], "timestamp": r[1].isoformat(), "is_out_of_spec": r[2] == "OUT_OF_SPEC"}
        for r in sand_rows
    ]

    # Fetch rejection points
    rej_rows = db.query(
        RejectionRecord.rejection_rate,
        RejectionRecord.rejected_qty,
        RejectionRecord.inspected_qty,
        RejectionRecord.timestamp
    ).filter(
        RejectionRecord.line_code == line_code.upper(),
        RejectionRecord.defect_category_id == defect.id
    ).order_by(RejectionRecord.timestamp.asc()).all()

    rejection_points = [
        {"rejection_rate": r[0], "rejected_qty": r[1], "inspected_qty": r[2], "timestamp": r[3].isoformat()}
        for r in rej_rows
    ]

    result = CorrelationEngine.analyze_pair(
        parameter_name=param.name,
        defect_name=defect.name,
        line_code=line_code.upper(),
        sand_points=sand_points,
        rejection_points=rejection_points,
        lag_hours=lag_hours,
        usl=param.usl,
        lsl=param.lsl
    )
    result.update({
        "parameter_code": param.code,
        "defect_code": defect.code,
        "parameter_unit": param.unit,
        "usl": param.usl,
        "lsl": param.lsl
    })
    return result

@router.get("/candidate-root-causes")
def get_candidate_root_causes(
    line_code: str = Query("D2"),
    lag_hours: int = Query(12),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Automated scan of top physical sand parameters against major defects
    to identify candidate root-cause associations with statistically significant relationships.
    """
    parameters_to_scan = ["MOISTURE", "COMPACT", "GCS", "PERM", "ACTIVE_CLAY"]
    defects_to_scan = ["POROSITY", "BLOWHOLE", "SAND_INCLUSION", "SCABBING"]

    candidates = []

    for p_code in parameters_to_scan:
        param = db.query(Parameter).filter(Parameter.code == p_code).first()
        if not param:
            continue

        sand_rows = db.query(
            SandTestValue.measured_value,
            SandTestRecord.timestamp,
            SandTestValue.status
        ).join(SandTestRecord).filter(
            SandTestRecord.line_code == line_code.upper(),
            SandTestValue.parameter_id == param.id
        ).order_by(SandTestRecord.timestamp.asc()).all()

        sand_points = [{"value": r[0], "timestamp": r[1].isoformat(), "is_out_of_spec": r[2] == "OUT_OF_SPEC"} for r in sand_rows]

        for d_code in defects_to_scan:
            defect = db.query(DefectCategory).filter(DefectCategory.code == d_code).first()
            if not defect:
                continue

            rej_rows = db.query(
                RejectionRecord.rejection_rate,
                RejectionRecord.rejected_qty,
                RejectionRecord.inspected_qty,
                RejectionRecord.timestamp
            ).filter(
                RejectionRecord.line_code == line_code.upper(),
                RejectionRecord.defect_category_id == defect.id
            ).order_by(RejectionRecord.timestamp.asc()).all()

            rej_points = [{"rejection_rate": r[0], "rejected_qty": r[1], "inspected_qty": r[2], "timestamp": r[3].isoformat()} for r in rej_rows]

            res = CorrelationEngine.analyze_pair(
                parameter_name=param.name,
                defect_name=defect.name,
                line_code=line_code.upper(),
                sand_points=sand_points,
                rejection_points=rej_points,
                lag_hours=lag_hours,
                usl=param.usl,
                lsl=param.lsl
            )

            # Highlight if statistically significant and strong or moderate
            if res.get("is_statistically_significant") and abs(res.get("pearson_r", 0)) >= 0.35:
                candidates.append({
                    "parameter_code": p_code,
                    "parameter_name": param.name,
                    "defect_code": d_code,
                    "defect_name": defect.name,
                    "pearson_r": res.get("pearson_r"),
                    "p_value": res.get("pearson_p_value"),
                    "relationship_strength": res.get("relationship_strength"),
                    "rejection_ratio": res.get("group_comparison", {}).get("rejection_ratio"),
                    "insight": res.get("insight")
                })

    return {
        "line_code": line_code.upper(),
        "lag_hours": lag_hours,
        "candidate_count": len(candidates),
        "candidates": sorted(candidates, key=lambda x: abs(x["pearson_r"]), reverse=True)
    }
