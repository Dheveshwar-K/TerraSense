from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.sand_test import SandTestRecord, SandTestValue, TestCorrectionRequest
from app.models.parameter import Parameter
from app.models.user import User
from app.schemas.sand_test import (
    SandTestRecordResponse, SandTestValueResponse, SandTestCreate,
    CorrectionRequestCreate
)
from app.api.deps import get_current_user, require_role, log_audit
from app.services.alert_engine import AlertEngine

router = APIRouter()

@router.get("", response_model=list[SandTestRecordResponse])
def list_sand_tests(
    line_code: str = None,
    test_type: str = None,
    start_date: str = None,
    end_date: str = None,
    shift: int = None,
    status: str = None,
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(SandTestRecord)
    if line_code and line_code != "ALL":
        query = query.filter(SandTestRecord.line_code == line_code.upper())
    if test_type:
        query = query.filter(SandTestRecord.test_type == test_type.upper())
    if start_date:
        query = query.filter(SandTestRecord.test_date >= start_date)
    if end_date:
        query = query.filter(SandTestRecord.test_date <= end_date)
    if shift:
        query = query.filter(SandTestRecord.shift == shift)
    if status:
        query = query.filter(SandTestRecord.status == status.upper())

    limit = limit if isinstance(limit, int) else 100
    records = query.order_by(SandTestRecord.timestamp.desc()).limit(limit).all()

    # Format response
    res = []
    for r in records:
        val_responses = []
        for v in r.values:
            val_responses.append(SandTestValueResponse(
                id=v.id,
                parameter_id=v.parameter_id,
                parameter_name=v.parameter.name if v.parameter else "Unknown",
                parameter_code=v.parameter.code if v.parameter else "UNK",
                measured_value=v.measured_value,
                unit=v.unit,
                status=v.status,
                is_corrected=v.is_corrected,
                original_value=v.original_value,
                correction_reason=v.correction_reason
            ))

        res.append(SandTestRecordResponse(
            id=r.id,
            test_number=r.test_number,
            line_code=r.line_code,
            test_type=r.test_type,
            test_date=r.test_date,
            shift=r.shift,
            test_hour=r.test_hour,
            timestamp=r.timestamp,
            batch_number=r.batch_number,
            status=r.status,
            notes=r.notes,
            operator_name=r.operator.full_name if r.operator else "Unknown",
            values=val_responses
        ))
    return res

@router.post("", response_model=SandTestRecordResponse)
def create_sand_test(
    test_in: SandTestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Check duplicate prevention
    existing = db.query(SandTestRecord).filter(
        SandTestRecord.line_code == test_in.line_code.upper(),
        SandTestRecord.test_date == test_in.test_date,
        SandTestRecord.shift == test_in.shift,
        SandTestRecord.test_hour == test_in.test_hour,
        SandTestRecord.test_type == test_in.test_type.upper()
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"A test entry already exists for Line {test_in.line_code}, Date {test_in.test_date}, Shift {test_in.shift}, Hour {test_in.test_hour} ({existing.test_number}). Please request a data correction if revision is needed."
        )

    now = datetime.now(timezone.utc)
    test_num = f"ST-{test_in.line_code.upper()}-{test_in.test_date.replace('-','')}-H{test_in.test_hour:02d}-{now.strftime('%M%S')}"

    record = SandTestRecord(
        test_number=test_num,
        line_code=test_in.line_code.upper(),
        test_type=test_in.test_type.upper(),
        test_date=test_in.test_date,
        shift=test_in.shift,
        test_hour=test_in.test_hour,
        timestamp=now,
        batch_number=test_in.batch_number,
        operator_id=current_user.id,
        status="CONFORMING",
        notes=test_in.notes
    )
    db.add(record)
    db.flush()

    record_status = "CONFORMING"
    values_created = []

    for v_in in test_in.values:
        param = db.query(Parameter).filter(Parameter.id == v_in.parameter_id).first()
        if not param:
            continue

        # Data validation check
        if param.data_validation_min is not None and v_in.measured_value < param.data_validation_min:
            raise HTTPException(status_code=400, detail=f"Value {v_in.measured_value} for {param.name} is below physical sensor limit ({param.data_validation_min})")
        if param.data_validation_max is not None and v_in.measured_value > param.data_validation_max:
            raise HTTPException(status_code=400, detail=f"Value {v_in.measured_value} for {param.name} exceeds physical sensor limit ({param.data_validation_max})")

        # Compare against specification limits
        v_status = "OK"
        if param.usl is not None and v_in.measured_value > param.usl:
            v_status = "OUT_OF_SPEC"
            record_status = "OUT_OF_SPEC"
        elif param.lsl is not None and v_in.measured_value < param.lsl:
            v_status = "OUT_OF_SPEC"
            record_status = "OUT_OF_SPEC"
        elif (param.usl is not None and v_in.measured_value > (param.usl - 0.15 * (param.usl - param.lsl))) or \
             (param.lsl is not None and v_in.measured_value < (param.lsl + 0.15 * (param.usl - param.lsl))):
            v_status = "WARNING"
            if record_status == "CONFORMING":
                record_status = "WARNING"

        test_val = SandTestValue(
            record_id=record.id,
            parameter_id=param.id,
            measured_value=v_in.measured_value,
            unit=param.unit,
            specification_revision=param.current_revision,
            status=v_status
        )
        db.add(test_val)
        values_created.append(test_val)

    record.status = record_status
    db.commit()
    db.refresh(record)

    # Trigger Quality Alert Engine
    AlertEngine.process_sand_test_record(db, record)

    # IATF Audit Trail
    log_audit(
        db, current_user, "CREATE", "SandTestRecord", str(record.id),
        new_value={"test_number": record.test_number, "line": record.line_code, "status": record.status},
        reason="Digital shop-floor test entry"
    )

    # Build response
    val_responses = [
        SandTestValueResponse(
            id=v.id,
            parameter_id=v.parameter_id,
            parameter_name=v.parameter.name,
            parameter_code=v.parameter.code,
            measured_value=v.measured_value,
            unit=v.unit,
            status=v.status,
            is_corrected=v.is_corrected,
            original_value=v.original_value,
            correction_reason=v.correction_reason
        ) for v in record.values
    ]

    return SandTestRecordResponse(
        id=record.id,
        test_number=record.test_number,
        line_code=record.line_code,
        test_type=record.test_type,
        test_date=record.test_date,
        shift=record.shift,
        test_hour=record.test_hour,
        timestamp=record.timestamp,
        batch_number=record.batch_number,
        status=record.status,
        notes=record.notes,
        operator_name=current_user.full_name,
        values=val_responses
    )

@router.post("/corrections", response_model=dict)
def request_test_correction(
    req_in: CorrectionRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    val = db.query(SandTestValue).filter(SandTestValue.id == req_in.value_id).first()
    if not val:
        raise HTTPException(status_code=404, detail="Test value not found")

    corr = TestCorrectionRequest(
        value_id=val.id,
        requested_value=req_in.requested_value,
        reason=req_in.reason,
        requested_by_id=current_user.id,
        status="PENDING"
    )
    db.add(corr)
    db.commit()
    db.refresh(corr)

    log_audit(
        db, current_user, "CORRECTION_REQUESTED", "SandTestValue", str(val.id),
        old_value={"value": val.measured_value},
        new_value={"requested": req_in.requested_value},
        reason=req_in.reason
    )

    return {"message": "Correction request submitted for Quality Engineer review", "request_id": corr.id}

@router.post("/corrections/{request_id}/approve", response_model=dict)
def approve_test_correction(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["quality_engineer", "quality_manager", "admin"]))
):
    corr = db.query(TestCorrectionRequest).filter(TestCorrectionRequest.id == request_id).first()
    if not corr:
        raise HTTPException(status_code=404, detail="Correction request not found")
    if corr.status != "PENDING":
        raise HTTPException(status_code=400, detail="Correction request already reviewed")

    val = db.query(SandTestValue).filter(SandTestValue.id == corr.value_id).first()
    if not val:
        raise HTTPException(status_code=404, detail="Target test value not found")

    # Update value with audit preservation (never silent overwrite!)
    val.original_value = val.measured_value
    val.measured_value = corr.requested_value
    val.is_corrected = True
    val.correction_reason = corr.reason
    val.corrected_by_id = current_user.id
    val.corrected_at = datetime.now(timezone.utc)

    # Recalculate status
    param = val.parameter
    if param:
        if param.usl is not None and val.measured_value > param.usl:
            val.status = "OUT_OF_SPEC"
        elif param.lsl is not None and val.measured_value < param.lsl:
            val.status = "OUT_OF_SPEC"
        else:
            val.status = "OK"

    corr.status = "APPROVED"
    corr.reviewed_by_id = current_user.id
    corr.reviewed_at = datetime.now(timezone.utc)

    db.commit()

    log_audit(
        db, current_user, "CORRECTION_APPROVED", "SandTestValue", str(val.id),
        old_value={"value": val.original_value},
        new_value={"value": val.measured_value},
        reason=f"Approved correction request #{corr.id}: {corr.reason}"
    )

    return {"message": "Correction approved and value updated with full audit trail."}
