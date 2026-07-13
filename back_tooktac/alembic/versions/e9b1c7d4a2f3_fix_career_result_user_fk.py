"""fix career diagnosis result user foreign key

Revision ID: e9b1c7d4a2f3
Revises: d4e8a6b2c1f0
Create Date: 2026-07-13 00:00:01.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e9b1c7d4a2f3"
down_revision: Union[str, Sequence[str], None] = "d4e8a6b2c1f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _fk_to_user_username(inspector) -> str | None:
    for fk in inspector.get_foreign_keys("career_diagnosis_result"):
        if (
            fk.get("referred_table") == "user"
            and fk.get("referred_columns") == ["username"]
            and fk.get("constrained_columns") == ["user_id"]
        ):
            return fk.get("name")
    return None


def _fk_to_user_id_exists(inspector) -> bool:
    return any(
        fk.get("referred_table") == "user"
        and fk.get("referred_columns") == ["id"]
        and fk.get("constrained_columns") == ["user_id"]
        for fk in inspector.get_foreign_keys("career_diagnosis_result")
    )


def _column_type_name(inspector, column_name: str) -> str:
    for column in inspector.get_columns("career_diagnosis_result"):
        if column["name"] == column_name:
            return column["type"].__class__.__name__.lower()
    return ""


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("career_diagnosis_result"):
        return

    bad_fk_name = _fk_to_user_username(inspector)
    user_id_type = _column_type_name(inspector, "user_id")

    if bad_fk_name:
        op.drop_constraint(bad_fk_name, "career_diagnosis_result", type_="foreignkey")

    if "char" in user_id_type or "string" in user_id_type:
        op.add_column("career_diagnosis_result", sa.Column("user_id_int", sa.Integer(), nullable=True))
        op.execute(
            """
            UPDATE career_diagnosis_result AS c
            JOIN user AS u ON c.user_id = u.username
            SET c.user_id_int = u.id
            """
        )
        unresolved = bind.execute(
            sa.text("SELECT COUNT(*) FROM career_diagnosis_result WHERE user_id_int IS NULL")
        ).scalar()
        if unresolved:
            raise RuntimeError("career_diagnosis_result has rows that cannot be mapped from username to user.id")

        op.drop_column("career_diagnosis_result", "user_id")
        op.alter_column(
            "career_diagnosis_result",
            "user_id_int",
            new_column_name="user_id",
            existing_type=sa.Integer(),
            nullable=False,
        )

    # Keep the table shape aligned with app.repository.career.CareerDiagnosisResult.
    op.alter_column(
        "career_diagnosis_result",
        "desired_job",
        existing_type=sa.String(length=100),
        nullable=True,
    )
    op.alter_column(
        "career_diagnosis_result",
        "total_score",
        existing_type=sa.Numeric(5, 2),
        type_=sa.Integer(),
        nullable=False,
    )

    inspector = sa.inspect(bind)
    if not _fk_to_user_id_exists(inspector):
        op.create_foreign_key(
            "fk_career_result_user_id",
            "career_diagnosis_result",
            "user",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("career_diagnosis_result"):
        return

    for fk in inspector.get_foreign_keys("career_diagnosis_result"):
        if (
            fk.get("referred_table") == "user"
            and fk.get("referred_columns") == ["id"]
            and fk.get("constrained_columns") == ["user_id"]
        ):
            op.drop_constraint(fk["name"], "career_diagnosis_result", type_="foreignkey")

    op.alter_column(
        "career_diagnosis_result",
        "total_score",
        existing_type=sa.Integer(),
        type_=sa.Numeric(5, 2),
        nullable=False,
    )
    op.alter_column(
        "career_diagnosis_result",
        "desired_job",
        existing_type=sa.String(length=100),
        nullable=False,
    )

