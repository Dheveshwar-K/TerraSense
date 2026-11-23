import pytest
from app.core.database import SessionLocal
from app.api.routes import auth, lines, analytics, spc, correlations, sand_tests, rejections
from app.schemas.user import UserLogin
from app.schemas.sand_test import SandTestCreate, ValueEntry
from app.models.user import User
from app.models.parameter import Parameter
from fastapi import HTTPException

@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()

@pytest.fixture
def admin_user(db):
    user = db.query(User).filter(User.username == "admin").first()
    assert user is not None
    return user

@pytest.fixture
def operator_user(db):
    user = db.query(User).filter(User.username == "operator").first()
    assert user is not None
    return user

def test_auth_login(db):
    res = auth.login(UserLogin(username="operator", password="operator123"), db=db)
    assert res["access_token"] is not None
    assert res["user"].role == "operator"

def test_get_lines(db, admin_user):
    all_lines = lines.get_lines(db=db, current_user=admin_user)
    assert len(all_lines) == 4
    codes = [l.code for l in all_lines]
    assert "D1" in codes and "D2" in codes and "D3" in codes and "D4" in codes

def test_dashboard_summary(db, admin_user):
    summary = analytics.get_dashboard_summary(db=db, current_user=admin_user)
    assert "metrics" in summary
    assert "lines" in summary
    assert len(summary["lines"]) == 4
    assert summary["metrics"]["total_tests_week"] > 0

def test_spc_imr_endpoint(db, admin_user):
    chart = spc.get_imr_chart(
        line_code="D1",
        parameter_code="MOISTURE",
        db=db,
        current_user=admin_user
    )
    assert chart["chart_type"] == "I-MR"
    assert "i_chart" in chart
    assert "mr_chart" in chart
    assert len(chart["points"]) > 0
    assert chart["mean"] > 0

def test_process_capability_endpoint(db, admin_user):
    cap = spc.get_process_capability(
        line_code="D1",
        parameter_code="MOISTURE",
        db=db,
        current_user=admin_user
    )
    assert cap["can_calculate"] is True
    assert cap["cp"] is not None
    assert cap["cpk"] is not None
    assert cap["sigma_within"] > 0

def test_correlation_pair_endpoint(db, admin_user):
    corr = correlations.analyze_correlation_pair(
        line_code="D2",
        parameter_code="MOISTURE",
        defect_code="POROSITY",
        lag_hours=12,
        db=db,
        current_user=admin_user
    )
    assert "pearson_r" in corr
    assert "insight" in corr
    assert "correlation does not prove causation" in corr["insight"].lower()

def test_pareto_analysis_endpoint(db, admin_user):
    pareto = rejections.get_defect_pareto(
        line_code="ALL",
        db=db,
        current_user=admin_user
    )
    assert "items" in pareto
    assert len(pareto["items"]) > 0
    assert pareto["total_rejected"] > 0

def test_sand_test_entry_and_duplicate_prevention(db, operator_user):
    from app.models.sand_test import SandTestRecord
    # Cleanup prior test entry if present
    db.query(SandTestRecord).filter(
        SandTestRecord.line_code == "D4",
        SandTestRecord.test_date == "2026-11-25",
        SandTestRecord.shift == 2,
        SandTestRecord.test_hour == 16
    ).delete()
    db.commit()

    param = db.query(Parameter).filter(Parameter.code == "MOISTURE").first()
    assert param is not None

    payload = SandTestCreate(
        line_code="D4",
        test_type="HOURLY_PHYSICAL",
        test_date="2026-11-25",
        shift=2,
        test_hour=16,
        batch_number="BAT-D4-TEST",
        notes="Automated test entry",
        values=[ValueEntry(parameter_id=param.id, measured_value=3.38)]
    )

    # 1. Create test
    res = sand_tests.create_sand_test(test_in=payload, db=db, current_user=operator_user)
    assert res.line_code == "D4"
    assert res.test_date == "2026-11-25"
    assert res.shift == 2
    assert res.test_hour == 16

    # 2. Duplicate submission must raise HTTPException 400
    with pytest.raises(HTTPException) as exc_info:
        sand_tests.create_sand_test(test_in=payload, db=db, current_user=operator_user)
    assert exc_info.value.status_code == 400
    assert "already exists" in exc_info.value.detail.lower()
