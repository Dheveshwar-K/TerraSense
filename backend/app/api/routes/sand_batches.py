import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import get_client_ip, get_current_user, log_audit, require_role
from app.core.database import get_db
from app.models.line import ProductionLine
from app.models.sand_batch import SandBatch
from app.models.user import User
from app.schemas.sand_batch import SandBatchCreate, SandBatchResponse

router = APIRouter()


@router.get("", response_model=list[SandBatchResponse])
def list_sand_batches(
    line_code: str = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(SandBatch)
    if line_code and line_code != "ALL":
        query = query.filter(SandBatch.line_code == line_code.upper())
    limit = limit if isinstance(limit, int) else 50
    return query.order_by(SandBatch.timestamp.desc(), SandBatch.id.desc()).limit(limit).all()


@router.post("", response_model=SandBatchResponse)
def create_sand_batch(
    batch_in: SandBatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["operator", "quality_engineer", "supervisor", "quality_manager", "admin"])),
    request: Request = None,
):
    line_code = batch_in.line_code.upper()
    line = db.query(ProductionLine).filter(ProductionLine.code == line_code, ProductionLine.is_active == True).first()
    if not line:
        raise HTTPException(status_code=400, detail=f"Invalid or inactive production line '{line_code}'")

    now = datetime.now(timezone.utc)
    batch_num = f"BAT-{line_code}-{now.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"

    batch = SandBatch(
        batch_number=batch_num,
        line_code=line_code,
        muller_id=batch_in.muller_id,
        batch_weight_kg=batch_in.batch_weight_kg,
        bentonite_addition_kg=batch_in.bentonite_addition_kg,
        coal_dust_addition_kg=batch_in.coal_dust_addition_kg,
        new_sand_addition_kg=batch_in.new_sand_addition_kg,
        return_sand_kg=batch_in.return_sand_kg,
        water_addition_liters=batch_in.water_addition_liters,
        cycle_time_seconds=batch_in.cycle_time_seconds,
        operator_id=current_user.id,
        timestamp=now,
        notes=batch_in.notes,
    )
    db.add(batch)
    db.flush()

    log_audit(
        db,
        current_user,
        "CREATE",
        "SandBatch",
        str(batch.id),
        new_value={"batch_number": batch.batch_number, "line": batch.line_code, "muller": batch.muller_id},
        reason="Logged muller sand batch preparation",
        ip_address=get_client_ip(request),
        commit=False,
    )
    db.commit()
    db.refresh(batch)
    return batch
