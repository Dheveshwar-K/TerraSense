import json
from typing import Optional, Any
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User
from app.models.audit import AuditLog

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    # Also check Authorization header directly if not caught by OAuth2PasswordBearer
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username: str = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload invalid"
        )

    user = db.query(User).filter(User.username == username, User.is_active == True).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    return user

def require_role(allowed_roles: list[str]):
    """
    Enforces Role-Based Access Control (RBAC).
    Allowed roles: 'operator', 'quality_engineer', 'supervisor', 'quality_manager', 'admin'
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        # admin or quality_manager has access to everything
        if current_user.role in ["admin", "quality_manager"]:
            return current_user
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: User role '{current_user.role}' lacks permission for this operation. Required: {allowed_roles}"
            )
        return current_user
    return role_checker

def log_audit(
    db: Session,
    user: Optional[User],
    action: str,
    entity_type: str,
    entity_id: str,
    old_value: Optional[Any] = None,
    new_value: Optional[Any] = None,
    reason: Optional[str] = None,
    ip_address: Optional[str] = None
):
    """
    Creates an immutable IATF audit trail record.
    """
    try:
        user_id = user.id if user else None
        user_name = user.full_name if user else "System/Automated"
        user_role = user.role if user else "system"

        old_str = json.dumps(old_value, default=str) if old_value is not None else None
        new_str = json.dumps(new_value, default=str) if new_value is not None else None

        audit = AuditLog(
            user_id=user_id,
            user_name=user_name,
            user_role=user_role,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            old_value=old_str,
            new_value=new_str,
            reason=reason,
            ip_address=ip_address
        )
        db.add(audit)
        db.commit()
    except Exception as e:
        print(f"Error logging audit: {e}")
