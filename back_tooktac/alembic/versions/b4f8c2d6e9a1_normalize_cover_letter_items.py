"""normalize cover letter question answer items

Revision ID: b4f8c2d6e9a1
Revises: f2a6c81d9e37
Create Date: 2026-07-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b4f8c2d6e9a1"
down_revision: Union[str, Sequence[str], None] = "f2a6c81d9e37"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(table_name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table_name)


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table(table_name):
        return False
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _split_legacy(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split("|")]


def _backfill_items_from_legacy_columns() -> None:
    bind = op.get_bind()
    if not (
        _has_table("cover_letter")
        and _has_table("cover_letter_item")
        and _has_column("cover_letter", "question_text")
        and _has_column("cover_letter", "answer_text")
    ):
        return

    existing_items = bind.execute(sa.text("SELECT COUNT(*) FROM cover_letter_item")).scalar()
    if existing_items:
        return

    rows = bind.execute(
        sa.text("SELECT id, question_text, answer_text FROM cover_letter ORDER BY id")
    ).mappings()
    for row in rows:
        questions = _split_legacy(row["question_text"])
        answers = _split_legacy(row["answer_text"])
        for index in range(max(len(questions), len(answers))):
            question = questions[index] if index < len(questions) else ""
            answer = answers[index] if index < len(answers) else ""
            if not question and not answer:
                continue
            bind.execute(
                sa.text(
                    """
                    INSERT INTO cover_letter_item
                        (cover_letter_id, sort_order, question_text, answer_text)
                    VALUES
                        (:cover_letter_id, :sort_order, :question_text, :answer_text)
                    """
                ),
                {
                    "cover_letter_id": row["id"],
                    "sort_order": index + 1,
                    "question_text": question,
                    "answer_text": answer,
                },
            )


def upgrade() -> None:
    if not _has_table("cover_letter_item"):
        op.create_table(
            "cover_letter_item",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("cover_letter_id", sa.Integer(), nullable=False),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("question_text", sa.Text(), nullable=False),
            sa.Column("answer_text", sa.Text(), nullable=False),
            sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.ForeignKeyConstraint(
                ["cover_letter_id"],
                ["cover_letter.id"],
                name="fk_cover_letter_item_cover_letter",
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
            mysql_collate="utf8mb4_0900_ai_ci",
        )
        op.create_index(
            "ix_cover_letter_item_cover_letter_sort",
            "cover_letter_item",
            ["cover_letter_id", "sort_order"],
        )

    _backfill_items_from_legacy_columns()

    if _has_column("cover_letter", "question_text"):
        op.drop_column("cover_letter", "question_text")
    if _has_column("cover_letter", "answer_text"):
        op.drop_column("cover_letter", "answer_text")


def downgrade() -> None:
    if _has_table("cover_letter"):
        if not _has_column("cover_letter", "question_text"):
            op.add_column("cover_letter", sa.Column("question_text", sa.Text(), nullable=True))
        if not _has_column("cover_letter", "answer_text"):
            op.add_column("cover_letter", sa.Column("answer_text", sa.Text(), nullable=True))

    if _has_table("cover_letter_item") and _has_table("cover_letter"):
        bind = op.get_bind()
        rows = bind.execute(
            sa.text(
                """
                SELECT cover_letter_id, sort_order, question_text, answer_text
                FROM cover_letter_item
                ORDER BY cover_letter_id, sort_order, id
                """
            )
        ).mappings()
        grouped: dict[int, dict[str, list[str]]] = {}
        for row in rows:
            grouped.setdefault(row["cover_letter_id"], {"questions": [], "answers": []})
            grouped[row["cover_letter_id"]]["questions"].append(row["question_text"])
            grouped[row["cover_letter_id"]]["answers"].append(row["answer_text"])

        for cover_letter_id, parts in grouped.items():
            bind.execute(
                sa.text(
                    """
                    UPDATE cover_letter
                    SET question_text = :question_text, answer_text = :answer_text
                    WHERE id = :cover_letter_id
                    """
                ),
                {
                    "cover_letter_id": cover_letter_id,
                    "question_text": "|".join(parts["questions"]),
                    "answer_text": "|".join(parts["answers"]),
                },
            )

    if _has_table("cover_letter_item"):
        op.drop_index("ix_cover_letter_item_cover_letter_sort", table_name="cover_letter_item")
        op.drop_table("cover_letter_item")
