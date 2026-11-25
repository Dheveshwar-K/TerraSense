import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_client_ip, get_current_user, log_audit, require_role
from app.core.database import get_db
from app.models.line import ProductionLine
from app.models.parameter import Parameter
from app.models.sand_test import SandTestRecord, SandTestValue, TestCorrectionRequest
from app.models.user import User
from app.schemas.sand_test import (
    CorrectionRequestCreate,
    CorrectionRequestResponse,
    CorrectionReviewRequest,
    SandTestCreate,
    SandTestRecordResponse,
    SandTestValueResponse,
)
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
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(SandTestRecord).options(
        joinedload(SandTestRecord.operator),
        joinedload(SandTestRecord.values).joinedload(SandTestValue.parameter),
    )
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
    offset = offset if isinstance(offset, int) else 0
    records = query.order_by(SandTestRecord.timestamp.desc(), SandTestRecord.id.desc()).offset(offset).limit(limit).all()

    res = []
    for r in records:
        val_responses = [
            SandTestValueResponse(
                id=v.id,
                parameter_id=v.parameter_id,
                parameter_name=v.parameter.name if v.parameter else "Unknown",
                parameter_code=v.parameter.code if v.parameter else "UNK",
                measured_value=v.measured_value,
                unit=v.unit,
                status=v.status,
                is_corrected=v.is_corrected,
                original_value=v.original_value,
                correction_reason=v.correction_reason,
            )
            for v in r.values
        ]
        res.append(
            SandTestRecordResponse(
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
                values=val_responses,
            )
        )
    return res


@router.post("", response_model=SandTestRecordResponse)
def create_sand_test(
    test_in: SandTestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    line_code = test_in.line_code.upper()
    test_type = test_in.test_type.upper()

    line = db.query(ProductionLine).filter(ProductionLine.code == line_code, ProductionLine.is_active == True).first()
    if not line:
        raise HTTPException(status_code=400, detail=f"Invalid or inactive production line '{line_code}'")

    existing = (
        db.query(SandTestRecord)
        .filter(
            SandTestRecord.line_code == line_code,
            SandTestRecord.test_date == test_in.test_date,
            SandTestRecord.shift == test_in.shift,
            SandTestRecord.test_hour == test_in.test_hour,
            SandTestRecord.test_type == test_type,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail=(
                f"A test entry already exists for Line {line_code}, Date {test_in.test_date}, "
                f"Shift {test_in.shift}, Hour {test_in.test_hour} ({existing.test_number}). "
                "Please request a data correction if revision is needed."
            ),
        )

    param_ids = [v.parameter_id for v in test_in.values]
    params_map = {
        p.id: p
        for p in db.query(Parameter).filter(Parameter.id.in_(param_ids), Parameter.is_active == True).all()
    }
    if not params_map:
        raise HTTPException(status_code=400, detail="No valid active parameters found in test submission")

    # Compute timestamp aligned with test_date and test_hour (hour 24 -> 23:59)
    parsed_date = datetime.strptime(test_in.test_date, "%Y-%m-%d")
    hour_val = 23 if test_in.test_hour == 24 else test_in.test_hour
    minute_val = 59 if test_in.test_hour == 24 else 15
    record_ts = parsed_date.replace(hour=hour_val, minute=minute_val, second=0, tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    suffix = uuid.uuid4().hex[:5].upper()
    test_num = f"ST-{line_code}-{test_in.test_date.replace('-', '')}-H{test_in.test_hour:02d}-{now.strftime('%H%M%S')}-{suffix}"

    record = SandTestRecord(
        test_number=test_num,
        line_code=line_code,
        test_type=test_type,
        test_date=test_in.test_date,
        shift=test_in.shift,
        test_hour=test_in.test_hour,
        timestamp=record_ts,
        batch_number=test_in.batch_number,
        operator_id=current_user.id,
        status="CONFORMING",
        notes=test_in.notes,
    )
    db.add(record)
    db.flush()

    record_status = "CONFORMING"
    seen_params: set[int] = set()

    for v_in in test_in.values:
        if v_in.parameter_id in seen_params:
            raise HTTPException(status_code=400, detail=f"Duplicate parameter_id {v_in.parameter_id} in submission")
        seen_params.add(v_in.parameter_id)

        param = params_map.get(v_in.parameter_id)
        if not param:
            raise HTTPException(status_code=404, detail=f"Parameter {v_in.parameter_id} not found or inactive")

        if param.data_validation_min is not None and v_in.measured_value < param.data_validation_min:
            raise HTTPException(
                status_code=400,
                detail=f"Value {v_in.measured_value} for {param.name} is below physical sensor limit ({param.data_validation_min})",
            )
        if param.data_validation_max is not None and v_in.measured_value > param.data_validation_max:
            raise HTTPException(
                status_code=400,
                detail=f"Value {v_in.measured_value} for {param.name} exceeds physical sensor limit ({param.data_validation_max})",
            )

        v_status = "OK"
        if param.usl is not None and v_in.measured_value > param.usl:
            v_status = "OUT_OF_SPEC"
            record_status = "OUT_OF_SPEC"
        elif param.lsl is not None and v_in.measured_value < param.lsl:
            v_status = "OUT_OF_SPEC"
            record_status = "OUT_OF_SPEC"
        elif (
            param.usl is not None
            and param.lsl is not None
            and param.usl > param.lsl
            and (
                v_in.measured_value > (param.usl - 0.15 * (param.usl - param.lsl))
                or v_in.measured_value < (param.lsl + 0.15 * (param.usl - param.lsl))
            )
        ):
            v_status = "WARNING"
            if record_status == "CONFORMING":
                record_status = "WARNING"

        test_val = SandTestValue(
            record_id=record.id,
            parameter_id=param.id,
            measured_value=v_in.measured_value,
            unit=param.unit,
            specification_revision=param.current_revision,
            status=v_status,
        )
        db.add(test_val)

    record.status = record_status
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Duplicate test submission detected for Line {line_code}, Date {test_in.test_date}, Shift {test_in.shift}, Hour {test_in.test_hour}.",
        )

    log_audit(
        db,
        current_user,
        "CREATE",
        "SandTestRecord",
        str(record.id),
        new_value={"test_number": record.test_number, "line": record.line_code, "status": record.status},
        reason="Digital shop-floor test entry",
        ip_address=get_client_ip(request),
        commit=False,
    )
    db.commit()
    db.refresh(record)

    # Evaluate alerts after record is persisted
    AlertEngine.process_sand_test_record(db, record)

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
            correction_reason=v.correction_reason,
        )
        for v in record.values
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
        values=val_responses,
    )


@router.get("/corrections", response_model=list[CorrectionRequestResponse])
def list_correction_requests(
    status_filter: str = Query(default="ALL", alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(TestCorrectionRequest).options(
        joinedload(TestCorrectionRequest.value).joinedload(SandTestValue.parameter),
        joinedload(TestCorrectionRequest.value).joinedload(SandTestValue.record),
        joinedload(TestCorrectionRequest.requested_by),
        joinedload(TestCorrectionRequest.reviewed_by),
    )
    if status_filter and status_filter != "ALL":
        query = query.filter(TestCorrectionRequest.status == status_filter.upper())

    reqs = query.order_by(TestCorrectionRequest.created_at.desc()).limit(100).all()
    res = []
    for c in reqs:
        val = c.value
        rec = val.record if val else None
        param = val.parameter if val else None
        res.append(
            CorrectionRequestResponse(
                id=c.id,
                value_id=c.value_id,
                test_number=rec.test_number if rec else None,
                line_code=rec.line_code if rec else None,
                parameter_name=param.name if param else None,
                current_value=val.measured_value if val else None,
                requested_value=c.requested_value,
                unit=val.unit if val else None,
                reason=c.reason,
                status=c.status,
                requested_by_name=c.requested_by.full_name if c.requested_by else None,
                reviewed_by_name=c.reviewed_by.full_name if c.reviewed_by else None,
                review_notes=c.review_notes,
                created_at=c.created_at,
            )
        )
    return res


@router.post("/corrections", response_model=dict)
def request_test_correction(
    req_in: CorrectionRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    val = db.query(SandTestValue).options(joinedload(SandTestValue.parameter)).filter(SandTestValue.id == req_in.value_id).first()
    if not val:
        raise HTTPException(status_code=404, detail="Test value not found")

    param = val.parameter
    if param:
        if param.data_validation_min is not None and req_in.requested_value < param.data_validation_min:
            raise HTTPException(status_code=400, detail=f"Requested value is below physical sensor limit ({param.data_validation_min})")
        if param.data_validation_max is not None and req_in.requested_value > param.data_validation_max:
            raise HTTPException(status_code=400, detail=f"Requested value exceeds physical sensor limit ({param.data_validation_max})")

    corr = TestCorrectionRequest(
        value_id=val.id,
        requested_value=req_in.requested_value,
        reason=req_in.reason.strip(),
        requested_by_id=current_user.id,
        status="PENDING",
    )
    db.add(corr)
    db.flush()

    log_audit(
        db,
        current_user,
        "CORRECTION_REQUESTED",
        "SandTestValue",
        str(val.id),
        old_value={"value": val.measured_value},
        new_value={"requested": req_in.requested_value},
        reason=req_in.reason.strip(),
        ip_address=get_client_ip(request),
        commit=False,
    )
    db.commit()
    db.refresh(corr)

    return {"message": "Correction request submitted for Quality Engineer review", "request_id": corr.id}


@router.post("/corrections/{request_id}/approve", response_model=dict)
def approve_test_correction(
    request_id: int,
    review_in: CorrectionReviewRequest = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["quality_engineer", "quality_manager", "admin"])),
    request: Request = None,
):
    corr = db.query(TestCorrectionRequest).filter(TestCorrectionRequest.id == request_id).first()
    if not corr:
        raise HTTPException(status_code=404, detail="Correction request not found")
    if corr.status != "PENDING":
        raise HTTPException(status_code=400, detail="Correction request already reviewed")

    val = db.query(SandTestValue).options(joinedload(SandTestValue.parameter), joinedload(SandTestValue.record)).filter(SandTestValue.id == corr.value_id).first()
    if not val:
        raise HTTPException(status_code=404, detail="Target test value not found")

    old_val = val.measured_value
    if not val.is_corrected:
        val.original_value = val.measured_value
    val.measured_value = corr.requested_value
    val.is_corrected = True
    val.correction_reason = corr.reason
    val.corrected_by_id = current_user.id
    val.corrected_at = datetime.now(timezone.utc)

    param = val.parameter
    if param:
        if param.usl is not None and val.measured_value > param.usl:
            val.status = "OUT_OF_SPEC"
        elif param.lsl is not None and val.measured_value < param.lsl:
            val.status = "OUT_OF_SPEC"
        elif (
            param.usl is not None
            and param.lsl is not None
            and param.usl > param.lsl
            and (
                val.measured_value > (param.usl - 0.15 * (param.usl - param.lsl))
                or val.measured_value < (param.lsl + 0.15 * (param.usl - param.lsl))
            )
        ):
            val.status = "WARNING"
        else:
            val.status = "OK"

    # Recompute parent record aggregate status
    if val.record:
        statuses = {v.status for v in val.record.values}
        if "OUT_OF_SPEC" in statuses:
            val.record.status = "OUT_OF_SPEC"
        elif "WARNING" in statuses:
            val.record.status = "WARNING"
        else:
            val.record.status = "CONFORMING"

    corr.status = "APPROVED"
    corr.reviewed_by_id = current_user.id
    corr.reviewed_at = datetime.now(timezone.utc)
    corr.review_notes = review_in.review_notes if review_in else None

    log_audit(
        db,
        current_user,
        "CORRECTION_APPROVED",
        "SandTestValue",
        str(val.id),
        old_value={"value": old_val},
        new_value={"value": val.measured_value},
        reason=f"Approved correction request #{corr.id}: {corr.reason}",
        ip_address=get_client_ip(request),
        commit=False,
    )
    db.commit()

    return {"message": "Correction approved and value updated with full audit trail."}


@router.post("/corrections/{request_id}/reject", response_model=dict)
def reject_test_correction(
    request_id: int,
    review_in: CorrectionReviewRequest = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["quality_engineer", "quality_manager", "admin"])),
    request: Request = None,
):
    corr = db.query(TestCorrectionRequest).filter(TestCorrectionRequest.id == request_id).first()
    if not corr:
        raise HTTPException(status_code=404, detail="Correction request not found")
    if corr.status != "PENDING":
        raise HTTPException(status_code=400, detail="Correction request already reviewed")

    corr.status = "REJECTED"
    corr.reviewed_by_id = current_user.id
    corr.reviewed_at = datetime.now(timezone.utc)
    corr.review_notes = (review_in.review_notes if review_in and review_in.review_notes else "Rejected by Quality Engineer")

    log_audit(
        db,
        current_user,
        "CORRECTION_REJECTED",
        "SandTestValue",
        str(corr.value_id),
        old_value={"status": "PENDING"},
        new_value={"status": "REJECTED", "notes": corr.review_notes},
        reason=f"Rejected correction request #{corr.id}: {corr.review_notes}",
        ip_address=get_client_ip(request),
        commit=False,
    )
    db.commit()
    return {"message": "Correction request rejected."}
