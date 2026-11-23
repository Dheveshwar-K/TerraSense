from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.seed_service import seed_foundry_data
from app.models.user import User
from app.api.deps import require_role

router = APIRouter()

@router.post("/seed", response_model=dict)
def trigger_seed_data(
    force: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["quality_manager", "admin"]))
):
    seed_foundry_data(db, force=force)
    return {"message": "Demo data successfully seeded for lines D1, D2, D3, D4."}
