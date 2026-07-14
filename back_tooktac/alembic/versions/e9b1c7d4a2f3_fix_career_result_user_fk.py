"""keep career diagnosis migration graph connected

Revision ID: e9b1c7d4a2f3
Revises: d4e8a6b2c1f0
Create Date: 2026-07-13 00:00:01.000000

This revision is intentionally a no-op.

It is kept so databases that were already stamped to e9b1c7d4a2f3 remain
connected to the migration graph. Any schema changes after this point must be
added in a new revision instead of editing this already-published revision.
"""
from typing import Sequence, Union


revision: str = "e9b1c7d4a2f3"
down_revision: Union[str, Sequence[str], None] = "d4e8a6b2c1f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
