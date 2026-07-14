"""use int for career diagnosis result id

Revision ID: f6b3a91c0d27
Revises: e9b1c7d4a2f3
Create Date: 2026-07-13 00:00:02.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f6b3a91c0d27"
down_revision: Union[str, Sequence[str], None] = "e9b1c7d4a2f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _get_id_column():
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("career_diagnosis_result"):
        return None
    for column in inspector.get_columns("career_diagnosis_result"):
        if column["name"] == "id":
            return column
    return None


def upgrade() -> None:
    id_column = _get_id_column()
    if id_column is None or not isinstance(id_column["type"], sa.BigInteger):
        return

    max_id = op.get_bind().execute(
        sa.text("SELECT COALESCE(MAX(id), 0) FROM career_diagnosis_result")
    ).scalar()
    if max_id > 2147483647:
        raise RuntimeError("career_diagnosis_result.id contains values too large for INT")

    op.execute("ALTER TABLE career_diagnosis_result MODIFY id INT NOT NULL AUTO_INCREMENT")


def downgrade() -> None:
    id_column = _get_id_column()
    if id_column is None or isinstance(id_column["type"], sa.BigInteger):
        return

    op.execute("ALTER TABLE career_diagnosis_result MODIFY id BIGINT NOT NULL AUTO_INCREMENT")
