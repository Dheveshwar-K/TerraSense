import logging
from datetime import datetime, timezone
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.database import Base
from app.services.audit_service import backfill_audit_chain

logger = logging.getLogger("PS010-Migrations")


def _ensure_migrations_table(conn) -> None:
    conn.execute(text(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version VARCHAR(50) PRIMARY KEY,
            description VARCHAR(255) NOT NULL,
            applied_at VARCHAR(64) NOT NULL
        )
        """
    ))


def _is_applied(conn, version: str) -> bool:
    res = conn.execute(
        text("SELECT 1 FROM schema_migrations WHERE version = :v"),
        {"v": version},
    ).fetchone()
    return res is not None


def _mark_applied(conn, version: str, description: str) -> None:
    conn.execute(
        text(
            "INSERT INTO schema_migrations (version, description, applied_at) "
            "VALUES (:v, :d, :t)"
        ),
        {
            "v": version,
            "d": description,
            "t": datetime.now(timezone.utc).isoformat(),
        },
    )


def _column_exists(inspector, table_name: str, column_name: str) -> bool:
    if not inspector.has_table(table_name):
        return False
    cols = {c["name"] for c in inspector.get_columns(table_name)}
    return column_name in cols


def _add_column_if_missing(conn, inspector, table: str, col: str, ddl_type: str) -> None:
    if inspector.has_table(table) and not _column_exists(inspector, table, col):
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {ddl_type}"))
        logger.info("Added column %s.%s", table, col)


def run_non_destructive_migrations(engine: Engine) -> list[str]:
    """
    Applies idempotent, non-destructive schema migrations and ensures all model tables exist.
    Never drops tables or destroys existing records.
    """
    # Import all models so Base.metadata knows every table
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    applied_now: list[str] = []

    with engine.begin() as conn:
        _ensure_migrations_table(conn)
        inspector = inspect(conn)

        # Migration 0001: Baseline registration
        if not _is_applied(conn, "0001_baseline"):
            _mark_applied(conn, "0001_baseline", "Baseline TerraSense schema registered")
            applied_now.append("0001_baseline")

        # Migration 0002: Security, Token Versioning, Optimistic Locking, Traceability & Audit Hash Chain
        if not _is_applied(conn, "0002_security_audit_integrity"):
            is_pg = engine.dialect.name == "postgresql"
            bool_false = "FALSE" if is_pg else "0"

            _add_column_if_missing(conn, inspector, "users", "token_version", "INTEGER NOT NULL DEFAULT 1")
            _add_column_if_missing(conn, inspector, "users", "must_change_password", f"BOOLEAN NOT NULL DEFAULT {bool_false}")
            _add_column_if_missing(conn, inspector, "users", "failed_login_attempts", "INTEGER NOT NULL DEFAULT 0")
            _add_column_if_missing(conn, inspector, "users", "locked_until", "TIMESTAMP")

            _add_column_if_missing(conn, inspector, "parameters", "version", "INTEGER NOT NULL DEFAULT 1")
            _add_column_if_missing(conn, inspector, "rejection_records", "inspector_id", "INTEGER")
            _add_column_if_missing(conn, inspector, "customer_complaints", "version", "INTEGER NOT NULL DEFAULT 1")
            _add_column_if_missing(conn, inspector, "quality_alerts", "version", "INTEGER NOT NULL DEFAULT 1")
            _add_column_if_missing(conn, inspector, "root_cause_investigations", "version", "INTEGER NOT NULL DEFAULT 1")
            _add_column_if_missing(conn, inspector, "root_cause_investigations", "updated_at", "TIMESTAMP")

            _add_column_if_missing(conn, inspector, "audit_logs", "sequence_no", "INTEGER")
            _add_column_if_missing(conn, inspector, "audit_logs", "prev_hash", "VARCHAR(64)")
            _add_column_if_missing(conn, inspector, "audit_logs", "record_hash", "VARCHAR(64)")
            _add_column_if_missing(conn, inspector, "audit_logs", "outcome", "VARCHAR(20) NOT NULL DEFAULT 'SUCCESS'")

            # Helpful composite indexes (IF NOT EXISTS supported in both SQLite 3.3+ and PostgreSQL 9.5+)
            index_ddls = [
                "CREATE INDEX IF NOT EXISTS ix_sand_test_line_date_ts ON sand_test_records (line_code, test_date, timestamp)",
                "CREATE INDEX IF NOT EXISTS ix_sand_val_param_record ON sand_test_values (parameter_id, record_id)",
                "CREATE INDEX IF NOT EXISTS ix_rejection_line_date_defect ON rejection_records (line_code, production_date, defect_category_id)",
                "CREATE INDEX IF NOT EXISTS ix_audit_logs_sequence_no ON audit_logs (sequence_no)",
                "CREATE INDEX IF NOT EXISTS ix_audit_logs_record_hash ON audit_logs (record_hash)",
            ]
            for ddl in index_ddls:
                conn.execute(text(ddl))

            _mark_applied(conn, "0002_security_audit_integrity", "Add token revocation, optimistic locking, traceability, and audit hash chain")
            applied_now.append("0002_security_audit_integrity")

    # Backfill hash chain on existing audit_logs rows without touching historical data
    with Session(bind=engine) as db:
        backfilled = backfill_audit_chain(db)
        if backfilled > 0:
            logger.info("Backfilled SHA-256 hash chain for %d legacy audit records.", backfilled)

    return applied_now
