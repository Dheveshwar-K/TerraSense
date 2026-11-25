from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import (
    get_client_ip,
    get_current_user,
    log_audit,
    login_rate_limiter,
    oauth2_scheme,
)
from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    needs_rehash,
    validate_password_strength,
    verify_password,
)
from app.models.user import RevokedToken, User
from app.schemas.user import (
    DemoSwitchRequest,
    PasswordChangeRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserLogin,
    UserResponse,
)

router = APIRouter()

MAX_FAILED_LOGINS = 5
LOCKOUT_MINUTES = 10


def _issue_tokens_for_user(user: User) -> dict:
    payload = {"sub": user.username, "role": user.role, "tv": user.token_version}
    access_token = create_access_token(data=payload)
    refresh_token = create_refresh_token(data=payload)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": user,
    }


@router.get("/config")
def get_auth_config():
    """Returns non-sensitive authentication mode metadata for UI rendering."""
    return {
        "demo_mode": settings.is_demo_enabled(),
        "environment": settings.ENVIRONMENT,
        "access_token_expire_minutes": settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    }


@router.post("/login", response_model=TokenResponse)
def login(login_data: UserLogin, db: Session = Depends(get_db), request: Request = None):
    client_ip = get_client_ip(request) or "unknown"
    rate_key = f"{client_ip}:{login_data.username.lower()}"
    login_rate_limiter.check_and_record(rate_key)

    user = db.query(User).filter(User.username == login_data.username).first()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    if user and user.locked_until and user.locked_until > now:
        log_audit(
            db,
            user,
            "LOGIN_FAILED",
            "User",
            str(user.id),
            reason="Account temporarily locked due to repeated failed login attempts",
            ip_address=client_ip,
            outcome="FAILURE",
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Account temporarily locked due to repeated failed login attempts. Try again later.",
        )

    if not user or not verify_password(login_data.password, user.hashed_password):
        if user:
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            if user.failed_login_attempts >= MAX_FAILED_LOGINS:
                user.locked_until = now + timedelta(minutes=LOCKOUT_MINUTES)
            db.commit()
        log_audit(
            db,
            user,
            "LOGIN_FAILED",
            "User",
            str(user.id) if user else login_data.username,
            reason=f"Failed login attempt for username '{login_data.username}'",
            ip_address=client_ip,
            outcome="FAILURE",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    if not user.is_active:
        log_audit(
            db,
            user,
            "LOGIN_FAILED",
            "User",
            str(user.id),
            reason="Attempted login to deactivated account",
            ip_address=client_ip,
            outcome="FAILURE",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    # Reset lockout counters and transparently upgrade legacy PBKDF2 hashes to scrypt
    user.failed_login_attempts = 0
    user.locked_until = None
    if needs_rehash(user.hashed_password):
        user.hashed_password = hash_password(login_data.password)
    db.commit()
    login_rate_limiter.reset(rate_key)

    log_audit(
        db,
        user,
        "LOGIN",
        "User",
        str(user.id),
        reason="User authenticated via credentials",
        ip_address=client_ip,
        outcome="SUCCESS",
    )
    return _issue_tokens_for_user(user)


@router.post("/demo-switch", response_model=TokenResponse)
def demo_switch_role(
    switch_req: DemoSwitchRequest,
    db: Session = Depends(get_db),
    request: Request = None,
):
    """
    Demo/development quick-entry endpoint by role and user ID.
    Strictly disabled in production and whenever DEMO_MODE=false.
    """
    if not settings.is_demo_enabled():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo role switching is disabled outside explicit demo/development mode.",
        )

    role_to_username = {
        "operator": "operator",
        "quality_engineer": "quality_engineer",
        "supervisor": "supervisor",
        "quality_manager": "admin",
        "admin": "admin",
    }
    user = None
    requested_uid = (switch_req.user_id or "").strip()
    if requested_uid:
        user = db.query(User).filter(User.username == requested_uid, User.is_active == True).first()
    if not user:
        target_username = role_to_username.get(switch_req.role)
        user = db.query(User).filter(User.username == target_username, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=404, detail="Demo persona account not found")

    client_ip = get_client_ip(request)
    log_audit(
        db,
        user,
        "DEMO_SWITCH",
        "User",
        str(user.id),
        reason=f"Quick-entered as role '{user.role}' (user_id='{requested_uid or user.username}')",
        ip_address=client_ip,
        outcome="SUCCESS",
    )
    return _issue_tokens_for_user(user)


@router.post("/refresh", response_model=TokenResponse)
def refresh_access_token(
    req: RefreshTokenRequest,
    db: Session = Depends(get_db),
    request: Request = None,
):
    payload = decode_token(req.refresh_token, expected_type="refresh")
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

    jti = payload.get("jti")
    username = payload.get("sub")
    if not jti or not username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed refresh token")

    revoked = db.query(RevokedToken.id).filter(RevokedToken.jti == jti).first()
    if revoked:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token already revoked")

    user = db.query(User).filter(User.username == username, User.is_active == True).first()
    if not user or (payload.get("tv") is not None and payload.get("tv") != user.token_version):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User session invalid or revoked")

    # Rotate refresh token: revoke the used refresh token JTI
    exp_ts = payload.get("exp")
    exp_dt = datetime.fromtimestamp(exp_ts, tz=timezone.utc).replace(tzinfo=None) if exp_ts else datetime.now(timezone.utc).replace(tzinfo=None)
    db.add(RevokedToken(jti=jti, user_id=user.id, token_type="refresh", expires_at=exp_dt))
    db.commit()

    return _issue_tokens_for_user(user)


@router.post("/logout")
def logout(
    refresh_token: Optional[str] = None,
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """Revokes current access token (and optional refresh token) via JTI revocation table."""
    for raw_tok, expected in ((token, "access"), (refresh_token, "refresh")):
        if not raw_tok:
            continue
        payload = decode_token(raw_tok, expected_type=expected)
        if payload and payload.get("jti"):
            jti = payload["jti"]
            exists = db.query(RevokedToken.id).filter(RevokedToken.jti == jti).first()
            if not exists:
                exp_ts = payload.get("exp")
                exp_dt = datetime.fromtimestamp(exp_ts, tz=timezone.utc).replace(tzinfo=None) if exp_ts else datetime.now(timezone.utc).replace(tzinfo=None)
                db.add(RevokedToken(jti=jti, user_id=current_user.id, token_type=expected, expires_at=exp_dt))

    log_audit(
        db,
        current_user,
        "LOGOUT",
        "User",
        str(current_user.id),
        reason="User signed out and token revoked",
        ip_address=get_client_ip(request),
        commit=False,
    )
    db.commit()
    return {"message": "Signed out successfully"}


@router.post("/change-password")
def change_password(
    req: PasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    if not verify_password(req.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")

    if req.current_password == req.new_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password must differ from current password")

    policy_err = validate_password_strength(req.new_password)
    if policy_err:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=policy_err)

    current_user.hashed_password = hash_password(req.new_password)
    current_user.must_change_password = False
    # Bump token_version to invalidate all prior sessions
    current_user.token_version = (current_user.token_version or 1) + 1

    log_audit(
        db,
        current_user,
        "PASSWORD_CHANGE",
        "User",
        str(current_user.id),
        reason="User updated account password",
        ip_address=get_client_ip(request),
        commit=False,
    )
    db.commit()
    return {"message": "Password changed successfully. Please sign in with your new password."}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user
