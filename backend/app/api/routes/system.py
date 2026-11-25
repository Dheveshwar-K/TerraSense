from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_client_ip, log_audit, require_role
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.services.seed_service import seed_foundry_data

router = APIRouter()


class SeedRequest(BaseModel):
    force: bool = False


@router.post("/seed", response_model=dict)
def trigger_seed_data(
    seed_req: SeedRequest = SeedRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["quality_manager", "admin"])),
    request: Request = None,
):
    if not settings.is_demo_enabled():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo database seeding is strictly disabled outside explicit demo mode.",
        )

    seed_foundry_data(db, force=seed_req.force)
    log_audit(
        db,
        current_user,
        "SYSTEM_SEED",
        "System",
        "DEMO_DATASET",
        new_value={"force": seed_req.force},
        reason="Triggered demo dataset initialization in demo mode",
        ip_address=get_client_ip(request),
    )
    return {"message": "Demo data successfully seeded for lines D1, D2, D3, D4."}
