from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_client_ip, log_audit, require_role
from app.core.database import get_db
from app.core.security import hash_password, validate_password_strength
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, UserUpdate

router = APIRouter()


@router.get("", response_model=list[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["quality_manager", "admin"])),
):
    return db.query(User).order_by(User.id.asc()).all()


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["quality_manager", "admin"])),
    request: Request = None,
):
    policy_err = validate_password_strength(user_in.password)
    if policy_err:
        raise HTTPException(status_code=400, detail=policy_err)

    if db.query(User).filter(User.username == user_in.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        username=user_in.username,
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=hash_password(user_in.password),
        role=user_in.role,
        is_active=user_in.is_active,
        must_change_password=True,
    )
    db.add(user)
    db.flush()

    log_audit(
        db,
        current_user,
        "CREATE",
        "User",
        str(user.id),
        new_value={"username": user.username, "role": user.role, "is_active": user.is_active},
        reason="Administrator provisioned user account",
        ip_address=get_client_ip(request),
        commit=False,
    )
    db.commit()
    db.refresh(user)
    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["quality_manager", "admin"])),
    request: Request = None,
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == current_user.id and user_in.is_active is False:
        raise HTTPException(status_code=400, detail="Administrators cannot deactivate their own active session account")
    if user.id == current_user.id and user_in.role is not None and user_in.role not in ("admin", "quality_manager"):
        raise HTTPException(status_code=400, detail="Administrators cannot demote their own role")

    old_state = {
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
    }

    if user_in.full_name is not None:
        user.full_name = user_in.full_name
    if user_in.email is not None:
        dup_email = db.query(User).filter(User.email == user_in.email, User.id != user.id).first()
        if dup_email:
            raise HTTPException(status_code=400, detail="Email already in use by another account")
        user.email = user_in.email
    if user_in.role is not None and user_in.role != user.role:
        user.role = user_in.role
        user.token_version = (user.token_version or 1) + 1
    if user_in.is_active is not None and user_in.is_active != user.is_active:
        user.is_active = user_in.is_active
        if not user.is_active:
            user.token_version = (user.token_version or 1) + 1
    if user_in.must_change_password is not None:
        user.must_change_password = user_in.must_change_password

    new_state = {
        "full_name": user.full_name,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
    }

    log_audit(
        db,
        current_user,
        "UPDATE",
        "User",
        str(user.id),
        old_value=old_state,
        new_value=new_state,
        reason="Administrator updated user account / RBAC permissions",
        ip_address=get_client_ip(request),
        commit=False,
    )
    db.commit()
    db.refresh(user)
    return user
