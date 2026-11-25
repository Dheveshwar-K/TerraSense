from datetime import datetime, timezone
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.requests import Request

from app.api import deps
from app.api.routes import alerts, audit, auth, complaints, parameters, rejections, reports, sand_tests, system, users
from app.core.config import Settings
from app.core.migrations import run_non_destructive_migrations
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    needs_rehash,
    verify_password,
)
from app.models.user import User
from app.schemas.parameter import ParameterUpdate
from app.schemas.rejection import RejectionCreate
from app.schemas.user import DemoSwitchRequest, PasswordChangeRequest, RefreshTokenRequest, UserCreate, UserLogin, UserUpdate
from app.services.seed_service import seed_foundry_data


def _make_request(path: str = "/api/test", token: str | None = None, ip: str = "10.0.0.5") -> Request:
    headers = []
    if token:
        headers.append((b"authorization", f"Bearer {token}".encode("latin-1")))
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": headers,
        "client": (ip, 50000),
        "query_string": b"",
    }
    return Request(scope)


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "demo")
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-at-least-thirty-two-characters-long")
    db_file = tmp_path / "sec_test.db"
    eng = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    run_non_destructive_migrations(eng)
    Session = sessionmaker(bind=eng)
    with Session() as db:
        seed_foundry_data(db, force=False)
        yield db


def test_password_hashing_and_legacy_compat():
    pwd = "IndustrialQuality4.0"
    hashed = hash_password(pwd)
    assert hashed.startswith("scrypt$")
    assert hashed != pwd
    assert verify_password(pwd, hashed) is True
    assert verify_password("WrongPassword", hashed) is False
    assert needs_rehash(hashed) is False

    import base64, hashlib, os
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", pwd.encode("utf-8"), salt, 100000)
    legacy = f"{base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"
    assert verify_password(pwd, legacy) is True
    assert needs_rehash(legacy) is True


def test_jwt_access_and_refresh_type_separation():
    payload = {"sub": "quality_engineer", "role": "quality_engineer", "tv": 1}
    access = create_access_token(payload)
    refresh = create_refresh_token(payload)

    assert decode_token(access, expected_type="access")["sub"] == "quality_engineer"
    assert decode_token(refresh, expected_type="access") is None
    assert decode_token(access, expected_type="refresh") is None
    assert decode_token(refresh, expected_type="refresh")["sub"] == "quality_engineer"


def test_production_config_security_guards(monkeypatch):
    s = Settings()

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SECRET_KEY", "FOUNDRY-QUALITY-4.0-PS010-SUPER-SECURE-KEY-2026")
    monkeypatch.setenv("DATABASE_URL", "postgresql://app:StrongPass99!@postgres:5432/foundry_quality")
    monkeypatch.setenv("DEMO_MODE", "false")
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        s.validate_runtime_settings()

    monkeypatch.setenv("SECRET_KEY", "a" * 48)
    monkeypatch.setenv("DEMO_MODE", "true")
    with pytest.raises(RuntimeError, match="DEMO_MODE"):
        s.validate_runtime_settings()

    monkeypatch.setenv("DEMO_MODE", "false")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///foundry_quality.db")
    with pytest.raises(RuntimeError, match="PostgreSQL"):
        s.validate_runtime_settings()

    monkeypatch.setenv("DATABASE_URL", "postgresql://foundry_user:foundry_pass@postgres:5432/foundry_quality")
    with pytest.raises(RuntimeError, match="placeholder database password"):
        s.validate_runtime_settings()

    monkeypatch.setenv("DATABASE_URL", "postgresql://terrasense_app:VeryStrongSecret987!@postgres:5432/foundry_quality")
    s.validate_runtime_settings()


def test_auth_lifecycle_refresh_rotation_logout_and_password_change(isolated_db, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.setenv("DEMO_MODE", "false")
    db = isolated_db

    # Demo switch and seed must be blocked when DEMO_MODE=false
    with pytest.raises(HTTPException) as exc:
        auth.demo_switch_role(DemoSwitchRequest(role="admin"), db=db, request=_make_request())
    assert exc.value.status_code == 403

    admin_user = db.query(User).filter(User.username == "admin").first()
    with pytest.raises(HTTPException) as exc_seed:
        system.trigger_seed_data(db=db, current_user=admin_user, request=_make_request())
    assert exc_seed.value.status_code == 403

    # Login issues access + refresh tokens
    login_res = auth.login(UserLogin(username="operator", password="operator123"), db=db, request=_make_request())
    access_1 = login_res["access_token"]
    refresh_1 = login_res["refresh_token"]

    # Token authenticates get_current_user
    op_user = deps.get_current_user(request=_make_request(token=access_1), token=access_1, db=db)
    assert op_user.username == "operator"

    # Refresh rotates refresh token and rejects reuse of old refresh_1
    ref_res = auth.refresh_access_token(RefreshTokenRequest(refresh_token=refresh_1), db=db, request=_make_request())
    access_2 = ref_res["access_token"]
    assert access_2 != access_1
    with pytest.raises(HTTPException) as exc_reuse:
        auth.refresh_access_token(RefreshTokenRequest(refresh_token=refresh_1), db=db, request=_make_request())
    assert exc_reuse.value.status_code == 401

    # Logout revokes access_2 JTI
    auth.logout(token=access_2, db=db, current_user=op_user, request=_make_request())
    with pytest.raises(HTTPException) as exc_revoked:
        deps.get_current_user(request=_make_request(token=access_2), token=access_2, db=db)
    assert exc_revoked.value.status_code == 401

    # Password change increments token_version and invalidates prior tokens
    login_res2 = auth.login(UserLogin(username="operator", password="operator123"), db=db, request=_make_request())
    access_3 = login_res2["access_token"]
    auth.change_password(
        PasswordChangeRequest(current_password="operator123", new_password="OperatorNewPass2026!"),
        db=db,
        current_user=op_user,
        request=_make_request(),
    )
    with pytest.raises(HTTPException) as exc_tv:
        deps.get_current_user(request=_make_request(token=access_3), token=access_3, db=db)
    assert exc_tv.value.status_code == 401


def test_rbac_role_enforcement(isolated_db):
    db = isolated_db
    op = db.query(User).filter(User.username == "operator").first()
    sup = db.query(User).filter(User.username == "supervisor").first()
    qe = db.query(User).filter(User.username == "quality_engineer").first()
    adm = db.query(User).filter(User.username == "admin").first()

    # Audit logs: operator forbidden, supervisor/QE/admin allowed
    with pytest.raises(HTTPException) as exc1:
        deps.require_role(["quality_engineer", "supervisor", "quality_manager", "admin"])(op)
    assert exc1.value.status_code == 403
    assert deps.require_role(["quality_engineer", "supervisor", "quality_manager", "admin"])(sup).id == sup.id

    # Spec modifications & Resolve Alerts & 8D CAPA: supervisor & operator forbidden, QE/admin allowed
    for blocked in (op, sup):
        with pytest.raises(HTTPException) as exc_qe:
            deps.require_role(["quality_engineer", "quality_manager", "admin"])(blocked)
        assert exc_qe.value.status_code == 403
    assert deps.require_role(["quality_engineer", "quality_manager", "admin"])(qe).id == qe.id

    # User Management: QE, supervisor, operator forbidden; admin/quality_manager allowed
    for non_adm in (op, sup, qe):
        with pytest.raises(HTTPException) as exc_adm:
            deps.require_role(["quality_manager", "admin"])(non_adm)
        assert exc_adm.value.status_code == 403
    assert deps.require_role(["quality_manager", "admin"])(adm).id == adm.id

    # Admin cannot deactivate or demote self
    with pytest.raises(HTTPException) as exc_self:
        users.update_user(adm.id, UserUpdate(is_active=False), db=db, current_user=adm, request=_make_request())
    assert exc_self.value.status_code == 400


def test_login_rate_limiting_and_lockout(isolated_db):
    db = isolated_db
    ip = "198.51.100.77"
    # 5 wrong attempts trigger account lock (429) on 6th attempt
    for i in range(5):
        with pytest.raises(HTTPException) as exc:
            auth.login(UserLogin(username="supervisor", password="wrong"), db=db, request=_make_request(ip=ip))
        assert exc.value.status_code == 401

    with pytest.raises(HTTPException) as exc_lock:
        auth.login(UserLogin(username="supervisor", password="super123"), db=db, request=_make_request(ip=ip))
    assert exc_lock.value.status_code == 429


def test_demo_switch_with_user_id_and_dev_mode(isolated_db, monkeypatch):
    s = Settings()
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("DEMO_MODE", raising=False)
    assert s.DEMO_MODE is True
    assert s.is_demo_enabled() is True

    db = isolated_db
    # Quick entry by role + explicit user_id succeeds in development/demo mode
    res = auth.demo_switch_role(
        DemoSwitchRequest(role="operator", user_id="operator"),
        db=db,
        request=_make_request(ip="10.0.0.9"),
    )
    assert res["access_token"]
    assert res["user"].username == "operator"
    assert res["user"].role == "operator"

    # Custom badge/user ID falls back to the selected role persona in dev/demo mode
    res_badge = auth.demo_switch_role(
        DemoSwitchRequest(role="operator", user_id="SHOP-OP-12"),
        db=db,
        request=_make_request(ip="10.0.0.9"),
    )
    assert res_badge["access_token"]
    assert res_badge["user"].role == "operator"

    # Production environment rejects demo switch
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DEMO_MODE", "false")
    with pytest.raises(HTTPException) as exc_prod:
        auth.demo_switch_role(
            DemoSwitchRequest(role="operator", user_id="operator"),
            db=db,
            request=_make_request(ip="10.0.0.9"),
        )
    assert exc_prod.value.status_code == 403

