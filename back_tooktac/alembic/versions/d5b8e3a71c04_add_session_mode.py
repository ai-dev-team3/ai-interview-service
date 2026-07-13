"""interview_session에 mode 추가 (practice / real)

Revision ID: d5b8e3a71c04
Revises: c3f7a1d94e26
Create Date: 2026-07-13

기존 세션은 전부 연습 면접이므로 practice로 백필한다.
server_default를 남겨 둔다 — 이 컬럼을 모르는 옛 코드가 INSERT해도 죽지 않는다.
"""
import sqlalchemy as sa
from alembic import op

revision = "d5b8e3a71c04"
down_revision = "c3f7a1d94e26"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "interview_session",
        sa.Column(
            "mode",
            sa.String(length=20),
            nullable=False,
            server_default="practice",
        ),
    )


def downgrade() -> None:
    op.drop_column("interview_session", "mode")
