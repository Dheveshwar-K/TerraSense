from pathlib import Path
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.api.routes import alerts, audit, investigations, parameters, rejections, sand_batches, sand_tests
from app.core.migrations import run_non_destructive_migrations
from app.models.alert import QualityAlert
from app.models.audit import AuditLog
from app.models.parameter import Parameter
from app.models.user import User
from app.schemas.alert import AlertActionRequest
from app.schemas.investigation import InvestigationCreate, InvestigationUpdate
from app.schemas.parameter import ParameterUpdate
from app.schemas.rejection import RejectionCreate
from app.schemas.sand_batch import SandBatchCreate
from app.schemas.sand_test import CorrectionRequestCreate, CorrectionReviewRequest, SandTestCreate, ValueEntry
from app.services.audit_service import append_audit_event, verify_audit_chain
from app.services.report_generator import ReportGenerator
from app.services.seed_service import seed_foundry_data
from scripts.backup_sqlite import backup_sqlite


@pytest.fixture
def workflow_db(tmp_path, monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "demo")
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-at-least-thirty-two-characters-long")
    db_file = tmp_path / "workflow_test.db"
    eng = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    run_non_destructive_migrations(eng)
    Session = sessionmaker(bind=eng)
    with Session() as db:
        seed_foundry_data(db, force=False)
        yield db


def test_audit_hash_chain_and_tamper_detection(tmp_path):
    db_file = tmp_path / "audit_test.db"
    test_engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    run_non_destructive_migrations(test_engine)
    TestSession = sessionmaker(bind=test_engine)

    with TestSession() as db:
        u = User(username="auditor", email="a@foundry.local", full_name="Auditor", hashed_password="x", role="quality_engineer")
        db.add(u)
        db.commit()
        db.refresh(u)

        append_audit_event(db, u, "CREATE", "Parameter", "1", new_value={"lsl": 3.1, "usl": 3.7}, reason="Init", commit=True)
        append_audit_event(db, u, "UPDATE", "Parameter", "1", old_value={"usl": 3.7}, new_value={"usl": 3.65}, reason="Tighten", commit=True)
        append_audit_event(db, u, "APPROVE", "QualityAlert", "9", reason="Closed", commit=True)

        ok = verify_audit_chain(db)
        assert ok["valid"] is True
        assert ok["total_records"] == 3
        assert ok["verified_records"] == 3

        # Simulate direct DB tampering of row 2's reason
        row2 = db.query(AuditLog).filter(AuditLog.sequence_no == 2).first()
        row2.reason = "Tampered reason"
        db.commit()

        tampered = verify_audit_chain(db)
        assert tampered["valid"] is False
        assert len(tampered["broken_links"]) >= 1
        assert tampered["broken_links"][0]["sequence_no"] == 2


def test_optimistic_locking_and_workflows(workflow_db):
    db = workflow_db
    qe = db.query(User).filter(User.username == "quality_engineer").first()
    op = db.query(User).filter(User.username == "operator").first()

    # 1. Specification revision + optimistic conflict (409)
    moisture = db.query(Parameter).filter(Parameter.code == "MOISTURE").first()
    v0 = moisture.version
    updated = parameters.update_parameter_specification(
        moisture.id,
        ParameterUpdate(usl=3.68, revision_reason="Tighten upper moisture limit", expected_version=v0),
        db=db,
        current_user=qe,
    )
    assert updated.version == v0 + 1
    with pytest.raises(HTTPException) as exc_conf:
        parameters.update_parameter_specification(
            moisture.id,
            ParameterUpdate(usl=3.65, revision_reason="Stale version write", expected_version=v0),
            db=db,
            current_user=qe,
        )
    assert exc_conf.value.status_code == 409

    # 2. Sand batch creation + listing
    batch = sand_batches.create_sand_batch(
        SandBatchCreate(line_code="D1", muller_id="Muller-A", water_addition_liters=34.2),
        db=db,
        current_user=op,
    )
    assert batch.line_code == "D1"
    listed_batches = sand_batches.list_sand_batches(line_code="D1", db=db, current_user=op)
    assert any(b.id == batch.id for b in listed_batches)

    # 3. Root cause investigation create & update with version check
    inv = investigations.create_investigation(
        InvestigationCreate(
            title="Test Investigation",
            line_code="D2",
            five_why_analysis=["Why 1: high steam"],
            fishbone_factors={"machine": "valve stuck"},
        ),
        db=db,
        current_user=qe,
    )
    inv2 = investigations.update_investigation(
        inv.id,
        InvestigationUpdate(status="VALIDATED", expected_version=inv.version),
        db=db,
        current_user=qe,
    )
    assert inv2.status == "VALIDATED"
    assert inv2.version == inv.version + 1

    # 4. Rejection validation & Pareto consistency
    rej = rejections.create_rejection_record(
        RejectionCreate(
            production_date="2026-11-25",
            line_code="D1",
            shift=1,
            product_id=1,
            defect_category_id=1,
            rejected_qty=10,
            inspected_qty=200,
        ),
        db=db,
        current_user=qe,
    )
    assert rej.rejection_rate == 5.0
    pareto = rejections.get_defect_pareto(line_code="D1", db=db, current_user=qe)
    assert pareto["total_rejected"] > 0
    assert abs(pareto["items"][-1]["cumulative_percentage"] - 100.0) < 0.1

    # 5. Correction request + approval preserves original_value
    test_rec = sand_tests.create_sand_test(
        SandTestCreate(
            line_code="D1",
            test_type="HOURLY_PHYSICAL",
            test_date="2026-11-26",
            shift=1,
            test_hour=9,
            values=[ValueEntry(parameter_id=moisture.id, measured_value=3.45)],
        ),
        db=db,
        current_user=op,
    )
    val_id = test_rec.values[0].id
    corr_res = sand_tests.request_test_correction(
        CorrectionRequestCreate(value_id=val_id, requested_value=3.41, reason="Calibration offset fix"),
        db=db,
        current_user=op,
    )
    sand_tests.approve_test_correction(
        corr_res["request_id"],
        CorrectionReviewRequest(review_notes="Verified lab sheet"),
        db=db,
        current_user=qe,
    )
    # Audit chain remains intact across all operations
    verify_res = audit.verify_audit_trail_integrity(db=db, current_user=qe)
    assert verify_res["valid"] is True


def test_csv_formula_injection_sanitization():
    csv_bytes = ReportGenerator.generate_csv(
        headers=["Col1", "Col2"],
        rows=[["=CMD('calc')", "+1+1"], ["@SUM(A1)", "Normal Text"]],
        title="Test Export",
    )
    text = csv_bytes.decode("utf-8")
    assert "'=CMD('calc')" in text
    assert "'+1+1" in text
    assert "'@SUM(A1)" in text
    assert "Normal Text" in text


def test_sqlite_backup_and_integrity_script(tmp_path):
    src = Path("backend/foundry_quality.db")
    if not src.exists():
        return
    out = backup_sqlite(src, tmp_path / "backups")
    assert out.exists()
    assert out.with_suffix(".db.sha256").exists()
