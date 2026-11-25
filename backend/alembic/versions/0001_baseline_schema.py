"""Initial baseline schema

Revision ID: 0001_baseline
Revises:
Create Date: 2026-11-25
"""
from typing import Sequence, Union
from alembic import op
from app.core.database import Base
import app.models  # noqa: F401

revision: str = "0001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    # Non-destructive policy: do not drop existing production tables automatically.
    pass
