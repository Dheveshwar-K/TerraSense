from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_client_ip, get_current_user, log_audit, require_role
from app.core.database import get_db
from app.models.parameter import Parameter, ParameterSpecification
from app.models.user import User
from app.schemas.parameter import (
    ParameterCreate,
    ParameterResponse,
    ParameterUpdate,
    SpecificationRevisionResponse,
)

router = APIRouter()


@router.get("", response_model=list[ParameterResponse])
def list_parameters(
    category: str = None,
    frequency: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Parameter).filter(Parameter.is_active == True)
    if category:
        query = query.filter(Parameter.category == category.upper())
    if frequency:
        query = query.filter(Parameter.frequency == frequency.upper())
    return query.order_by(Parameter.id).all()


@router.post("", response_model=ParameterResponse)
def create_parameter(
    param_in: ParameterCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["quality_engineer", "quality_manager", "admin"])),
    request: Request = None,
):
    existing = db.query(Parameter).filter(Parameter.code == param_in.code.upper()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Parameter code already exists")

    param = Parameter(
        code=param_in.code.upper(),
        name=param_in.name,
        description=param_in.description,
        category=param_in.category.upper(),
        unit=param_in.unit,
        frequency=param_in.frequency.upper(),
        applicable_lines=param_in.applicable_lines,
        target_value=param_in.target_value,
        lsl=param_in.lsl,
        usl=param_in.usl,
        lcl_historical=param_in.lcl_historical,
        ucl_historical=param_in.ucl_historical,
        testing_method=param_in.testing_method,
        data_validation_min=param_in.data_validation_min,
        data_validation_max=param_in.data_validation_max,
        current_revision=1,
        version=1,
    )
    db.add(param)
    db.flush()

    rev = ParameterSpecification(
        parameter_id=param.id,
        revision_number=1,
        target_value=param.target_value,
        lsl=param.lsl,
        usl=param.usl,
        change_reason="Initial specification setup",
        approved_by_id=current_user.id,
    )
    db.add(rev)

    log_audit(
        db,
        current_user,
        "CREATE",
        "Parameter",
        str(param.id),
        new_value=param_in.model_dump(),
        reason="Configured new testing parameter",
        ip_address=get_client_ip(request),
        commit=False,
    )
    db.commit()
    db.refresh(param)
    return param


@router.put("/{param_id}", response_model=ParameterResponse)
def update_parameter_specification(
    param_id: int,
    param_update: ParameterUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["quality_engineer", "quality_manager", "admin"])),
    request: Request = None,
):
    param = db.query(Parameter).filter(Parameter.id == param_id).first()
    if not param:
        raise HTTPException(status_code=404, detail="Parameter not found")

    if param_update.expected_version is not None and param.version != param_update.expected_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Specification was modified concurrently by another user. Refresh and retry.",
        )

    new_lsl = param_update.lsl if param_update.lsl is not None else param.lsl
    new_usl = param_update.usl if param_update.usl is not None else param.usl
    new_target = param_update.target_value if param_update.target_value is not None else param.target_value

    if new_lsl >= new_usl:
        raise HTTPException(status_code=400, detail="Lower Spec Limit (LSL) must be strictly less than Upper Spec Limit (USL)")
    if not (new_lsl <= new_target <= new_usl):
        raise HTTPException(status_code=400, detail="Target value must lie within [LSL, USL]")

    old_spec = {
        "target_value": param.target_value,
        "lsl": param.lsl,
        "usl": param.usl,
        "revision": param.current_revision,
        "version": param.version,
    }

    spec_changed = (
        new_target != param.target_value
        or new_lsl != param.lsl
        or new_usl != param.usl
    )

    if spec_changed and not (param_update.revision_reason and param_update.revision_reason.strip()):
        raise HTTPException(status_code=400, detail="Engineering change reason is mandatory when revising specification limits")

    param.target_value = new_target
    param.lsl = new_lsl
    param.usl = new_usl
    if param_update.name:
        param.name = param_update.name
    if param_update.testing_method:
        param.testing_method = param_update.testing_method

    if spec_changed:
        param.current_revision += 1
        rev = ParameterSpecification(
            parameter_id=param.id,
            revision_number=param.current_revision,
            target_value=param.target_value,
            lsl=param.lsl,
            usl=param.usl,
            change_reason=param_update.revision_reason.strip(),
            approved_by_id=current_user.id,
        )
        db.add(rev)

    param.version = (param.version or 1) + 1

    new_spec = {
        "target_value": param.target_value,
        "lsl": param.lsl,
        "usl": param.usl,
        "revision": param.current_revision,
        "version": param.version,
    }

    log_audit(
        db,
        current_user,
        "UPDATE",
        "ParameterSpecification",
        str(param.id),
        old_value=old_spec,
        new_value=new_spec,
        reason=param_update.revision_reason or "Parameter metadata updated",
        ip_address=get_client_ip(request),
        commit=False,
    )
    db.commit()
    db.refresh(param)
    return param


@router.get("/{param_id}/revisions", response_model=list[SpecificationRevisionResponse])
def get_parameter_revisions(
    param_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(ParameterSpecification)
        .filter(ParameterSpecification.parameter_id == param_id)
        .order_by(ParameterSpecification.revision_number.desc())
        .all()
    )
