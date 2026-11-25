from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.parameter import Parameter
from app.models.rejection import DefectCategory, RejectionRecord
from app.models.sand_test import SandTestRecord, SandTestValue
from app.models.user import User
from app.services.correlation_engine import CorrelationEngine, apply_benjamini_hochberg

router = APIRouter()


@router.get("/pair")
def analyze_correlation_pair(
    line_code: str = Query("D2", description="Production Line (D1, D2, D3, D4)"),
    parameter_code: str = Query("MOISTURE", description="Parameter Code (MOISTURE, COMPACT, GCS, PERM)"),
    defect_code: str = Query("POROSITY", description="Defect Code (POROSITY, BLOWHOLE, SAND_INCLUSION)"),
    lag_hours: int = Query(12, ge=0, le=168, description="Process lag hours (0, 6, 12, 24, 48, 72)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    param = db.query(Parameter).filter(Parameter.code == parameter_code.upper()).first()
    if not param:
        raise HTTPException(status_code=404, detail="Parameter not found")

    defect = db.query(DefectCategory).filter(DefectCategory.code == defect_code.upper()).first()
    if not defect:
        raise HTTPException(status_code=404, detail="Defect category not found")

    sand_rows = (
        db.query(
            SandTestValue.measured_value,
            SandTestRecord.timestamp,
            SandTestValue.status,
        )
        .join(SandTestRecord)
        .filter(
            SandTestRecord.line_code == line_code.upper(),
            SandTestValue.parameter_id == param.id,
        )
        .order_by(SandTestRecord.timestamp.asc())
        .all()
    )

    sand_points = [
        {"value": r[0], "timestamp": r[1].isoformat(), "is_out_of_spec": r[2] == "OUT_OF_SPEC"}
        for r in sand_rows
        if r[1] is not None
    ]

    rej_rows = (
        db.query(
            RejectionRecord.rejection_rate,
            RejectionRecord.rejected_qty,
            RejectionRecord.inspected_qty,
            RejectionRecord.timestamp,
        )
        .filter(
            RejectionRecord.line_code == line_code.upper(),
            RejectionRecord.defect_category_id == defect.id,
        )
        .order_by(RejectionRecord.timestamp.asc())
        .all()
    )

    rejection_points = [
        {"rejection_rate": r[0], "rejected_qty": r[1], "inspected_qty": r[2], "timestamp": r[3].isoformat()}
        for r in rej_rows
        if r[3] is not None
    ]

    result = CorrelationEngine.analyze_pair(
        parameter_name=param.name,
        defect_name=defect.name,
        line_code=line_code.upper(),
        sand_points=sand_points,
        rejection_points=rejection_points,
        lag_hours=lag_hours,
        usl=param.usl,
        lsl=param.lsl,
    )
    result.update({
        "parameter_code": param.code,
        "defect_code": defect.code,
        "parameter_unit": param.unit,
        "usl": param.usl,
        "lsl": param.lsl,
    })
    return result


@router.get("/candidate-root-causes")
def get_candidate_root_causes(
    line_code: str = Query("D2"),
    lag_hours: int = Query(12, ge=0, le=168),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Bulk-scans physical sand parameters against major defect categories with
    Benjamini-Hochberg False Discovery Rate (FDR) correction across tested pairs.
    """
    norm_line = line_code.upper()
    parameters_to_scan = ["MOISTURE", "COMPACT", "GCS", "PERM", "ACTIVE_CLAY"]
    defects_to_scan = ["POROSITY", "BLOWHOLE", "SAND_INCLUSION", "SCABBING"]

    params = db.query(Parameter).filter(Parameter.code.in_(parameters_to_scan)).all()
    param_by_code = {p.code: p for p in params}

    defects = db.query(DefectCategory).filter(DefectCategory.code.in_(defects_to_scan)).all()
    defect_by_code = {d.code: d for d in defects}

    param_ids = [p.id for p in params]
    defect_ids = [d.id for d in defects]

    sand_by_param: dict[int, list[dict]] = {pid: [] for pid in param_ids}
    if param_ids:
        sand_rows = (
            db.query(
                SandTestValue.parameter_id,
                SandTestValue.measured_value,
                SandTestRecord.timestamp,
                SandTestValue.status,
            )
            .join(SandTestRecord)
            .filter(
                SandTestRecord.line_code == norm_line,
                SandTestValue.parameter_id.in_(param_ids),
            )
            .order_by(SandTestRecord.timestamp.asc())
            .all()
        )
        for pid, val, ts, st in sand_rows:
            if ts is not None:
                sand_by_param[pid].append({"value": val, "timestamp": ts.isoformat(), "is_out_of_spec": st == "OUT_OF_SPEC"})

    rej_by_defect: dict[int, list[dict]] = {did: [] for did in defect_ids}
    if defect_ids:
        rej_rows = (
            db.query(
                RejectionRecord.defect_category_id,
                RejectionRecord.rejection_rate,
                RejectionRecord.rejected_qty,
                RejectionRecord.inspected_qty,
                RejectionRecord.timestamp,
            )
            .filter(
                RejectionRecord.line_code == norm_line,
                RejectionRecord.defect_category_id.in_(defect_ids),
            )
            .order_by(RejectionRecord.timestamp.asc())
            .all()
        )
        for did, rate, rqty, iqty, ts in rej_rows:
            if ts is not None:
                rej_by_defect[did].append({"rejection_rate": rate, "rejected_qty": rqty, "inspected_qty": iqty, "timestamp": ts.isoformat()})

    all_pair_results: list[dict] = []
    for p_code in parameters_to_scan:
        param = param_by_code.get(p_code)
        if not param:
            continue
        for d_code in defects_to_scan:
            defect = defect_by_code.get(d_code)
            if not defect:
                continue

            res = CorrelationEngine.analyze_pair(
                parameter_name=param.name,
                defect_name=defect.name,
                line_code=norm_line,
                sand_points=sand_by_param.get(param.id, []),
                rejection_points=rej_by_defect.get(defect.id, []),
                lag_hours=lag_hours,
                usl=param.usl,
                lsl=param.lsl,
            )
            if res.get("sample_size", 0) >= 5:
                all_pair_results.append({
                    "parameter_code": p_code,
                    "parameter_name": param.name,
                    "defect_code": d_code,
                    "defect_name": defect.name,
                    "res": res,
                })

    raw_p_vals = [float(item["res"].get("pearson_p_value", 1.0)) for item in all_pair_results]
    adj_p_vals = apply_benjamini_hochberg(raw_p_vals)

    candidates = []
    for idx, item in enumerate(all_pair_results):
        res = item["res"]
        adj_p = adj_p_vals[idx]
        r_val = res.get("pearson_r", 0.0)
        if res.get("is_statistically_significant") and abs(r_val) >= 0.35:
            candidates.append({
                "parameter_code": item["parameter_code"],
                "parameter_name": item["parameter_name"],
                "defect_code": item["defect_code"],
                "defect_name": item["defect_name"],
                "pearson_r": r_val,
                "p_value": res.get("pearson_p_value"),
                "adjusted_p_value": adj_p,
                "fdr_significant": adj_p < 0.05,
                "sample_size": res.get("sample_size"),
                "relationship_strength": res.get("relationship_strength"),
                "rejection_ratio": res.get("group_comparison", {}).get("rejection_ratio"),
                "insight": res.get("insight"),
            })

    return {
        "line_code": norm_line,
        "lag_hours": lag_hours,
        "tests_evaluated": len(all_pair_results),
        "multiple_testing_correction": "Benjamini-Hochberg FDR",
        "multiple_testing_note": (
            f"Evaluated {len(all_pair_results)} parameter-defect pairs. Adjusted p-values control the false discovery rate across multiple comparisons. "
            "Correlation does not establish causation."
        ),
        "candidate_count": len(candidates),
        "candidates": sorted(candidates, key=lambda x: abs(x["pearson_r"]), reverse=True),
    }
