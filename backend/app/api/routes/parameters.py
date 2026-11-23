from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.parameter import Parameter, ParameterSpecification
from app.models.user import User
from app.schemas.parameter import ParameterResponse, ParameterCreate, ParameterUpdate, SpecificationRevisionResponse
from app.api.deps import get_current_user, require_role, log_audit

router = APIRouter()

@router.get("", response_model=list[ParameterResponse])
def list_parameters(
    category: str = None,
    frequency: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
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
    current_user: User = Depends(require_role(["quality_engineer", "quality_manager", "admin"]))
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
        current_revision=1
    )
    db.add(param)
    db.commit()
    db.refresh(param)

    # Initial revision
    rev = ParameterSpecification(
        parameter_id=param.id,
        revision_number=1,
        target_value=param.target_value,
        lsl=param.lsl,
        usl=param.usl,
        change_reason="Initial specification setup",
        approved_by_id=current_user.id
    )
    db.add(rev)
    db.commit()

    log_audit(db, current_user, "CREATE", "Parameter", str(param.id), new_value=param_in.model_dump(), reason="Configured new testing parameter")
    return param

@router.put("/{param_id}", response_model=ParameterResponse)
def update_parameter_specification(
    param_id: int,
    param_update: ParameterUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["quality_engineer", "quality_manager", "admin"]))
):
    param = db.query(Parameter).filter(Parameter.id == param_id).first()
    if not param:
        raise HTTPException(status_code=404, detail="Parameter not found")

    old_spec = {
        "target_value": param.target_value,
        "lsl": param.lsl,
        "usl": param.usl,
        "revision": param.current_revision
    }

    spec_changed = False
    if param_update.target_value is not None and param_update.target_value != param.target_value:
        param.target_value = param_update.target_value
        spec_changed = True
    if param_update.lsl is not None and param_update.lsl != param.lsl:
        param.lsl = param_update.lsl
        spec_changed = True
    if param_update.usl is not None and param_update.usl != param.usl:
        param.usl = param_update.usl
        spec_changed = True
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
            change_reason=param_update.revision_reason or "Engineering specification revision",
            approved_by_id=current_user.id
        )
        db.add(rev)

    db.commit()
    db.refresh(param)

    new_spec = {
        "target_value": param.target_value,
        "lsl": param.lsl,
        "usl": param.usl,
        "revision": param.current_revision
    }
    log_audit(db, current_user, "UPDATE", "ParameterSpecification", str(param.id), old_value=old_spec, new_value=new_spec, reason=param_update.revision_reason)

    return param

@router.get("/{param_id}/revisions", response_model=list[SpecificationRevisionResponse])
def get_parameter_revisions(
    param_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(ParameterSpecification).filter(ParameterSpecification.parameter_id == param_id).order_by(ParameterSpecification.revision_number.desc()).all()
