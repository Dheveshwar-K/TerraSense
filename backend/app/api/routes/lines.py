from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.line import ProductionLine
from app.schemas.line import LineResponse
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter()

@router.get("", response_model=list[LineResponse])
def get_lines(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(ProductionLine).filter(ProductionLine.is_active == True).all()

@router.get("/{line_code}", response_model=LineResponse)
def get_line(
    line_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    line = db.query(ProductionLine).filter(ProductionLine.code == line_code.upper()).first()
    if not line:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Production line not found")
    return line
