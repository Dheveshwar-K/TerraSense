"""Security hardening, optimistic locking, traceability, and audit hash chain

Revision ID: 0002_hardening
Revises: 0001_baseline
Create Date: 2026-11-25
"""
from typing import Sequence, Union
from alembic import op
from app.core.migrations import run_non_destructive_migrations

revision: str = "0002_hardening"
down_revision: Union[str, None] = "0001_baseline"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    run_non_destructive_migrations(bind.engine)


def downgrade() -> None:
    # Non-destructive policy: retain audit and security columns on rollback.
    pass
