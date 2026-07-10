"""add resume_question table and backfill default self-introduction question

Revision ID: c3f7a1d94e26
Revises: a1c4e9f2b830
Create Date: 2026-07-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3f7a1d94e26'
down_revision: Union[str, Sequence[str], None] = 'a1c4e9f2b830'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# app/services/interview/plan.py 와 값을 맞춘다.
_DEFAULT_QUESTION_TEXT = "1분 자기소개 부탁드립니다."
_DEFAULT_QUESTION_TYPE = "행동형"


def upgrade() -> None:
    """Upgrade schema."""
    # 질문 생성을 이미 마쳤는지 표시. 사용자가 생성된 질문을 모두 지워도
    # 다음 조회 때 되살아나지 않게 한다.
    op.add_column(
        'resume',
        sa.Column('questions_generated', sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_table(
        'resume_question',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('resume_id', sa.Integer(), nullable=False),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('question_type', sa.String(length=50), nullable=False),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(['resume_id'], ['resume.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_resume_question_resume_id'), 'resume_question', ['resume_id'])

    # 기존 이력서마다 기본 자기소개 질문 1행을 넣는다.
    # LLM 생성 질문은 여기서 만들 수 없고, 최초 GET /resume/questions 때 지연 생성된다.
    op.execute(
        sa.text(
            "INSERT INTO resume_question "
            "(resume_id, question_text, question_type, is_default, sort_order, created_at) "
            "SELECT id, :text, :type, TRUE, 0, NOW() FROM resume"
        ).bindparams(text=_DEFAULT_QUESTION_TEXT, type=_DEFAULT_QUESTION_TYPE)
    )


def downgrade() -> None:
    """Downgrade schema.

    테이블을 통째로 지운다. 저장된 질문은 복구되지 않는다.
    인덱스를 따로 지우지 않는 이유: MySQL은 외래 키가 참조하는 인덱스의 삭제를
    거부한다(errno 1553). drop_table이 인덱스와 외래 키를 함께 제거한다.
    """
    op.drop_table('resume_question')
    op.drop_column('resume', 'questions_generated')
