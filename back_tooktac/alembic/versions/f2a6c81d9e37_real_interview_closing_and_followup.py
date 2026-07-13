"""실전 면접: 마지막 한마디 + 꼬리질문 표시

Revision ID: f2a6c81d9e37
Revises: a7c9d2e4f5b6
Create Date: 2026-07-13

interview_session.closing_remark
    실전 면접의 "마지막으로 하고 싶은 말씀"의 전사. 질문 행으로 만들지 않는다 —
    채점하지 않기 때문이다. 질문으로 취급하면 채점·리포트·백그라운드 분석 모든 곳에서
    빼야 하고, 한 군데만 빼먹어도 버그가 된다.

interview_question.is_follow_up
    직전 답변을 파고든 꼬리질문인지. 리포트 표시용이며 채점에는 영향이 없다.
    기존 질문은 전부 False 로 백필된다(server_default).
"""
import sqlalchemy as sa
from alembic import op

revision = "f2a6c81d9e37"
down_revision = "a7c9d2e4f5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "interview_session",
        sa.Column("closing_remark", sa.Text(), nullable=True),
    )
    op.add_column(
        "interview_question",
        sa.Column(
            "is_follow_up",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )


def downgrade() -> None:
    op.drop_column("interview_question", "is_follow_up")
    op.drop_column("interview_session", "closing_remark")
