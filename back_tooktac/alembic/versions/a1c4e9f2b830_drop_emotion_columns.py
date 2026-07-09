"""drop emotion columns from video_evaluation_result

Revision ID: a1c4e9f2b830
Revises: 07b67346fb67
Create Date: 2026-07-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1c4e9f2b830'
down_revision: Union[str, Sequence[str], None] = '07b67346fb67'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column('video_evaluation_result', 'emotion_score')
    op.drop_column('video_evaluation_result', 'emotion_best')
    op.drop_column('video_evaluation_result', 'tense_rate')
    op.drop_column('video_evaluation_result', 'negative_rate')
    op.drop_column('video_evaluation_result', 'neutral_rate')
    op.drop_column('video_evaluation_result', 'positive_rate')


def downgrade() -> None:
    """Downgrade schema.

    컬럼만 되살린다. 삭제된 감정 데이터는 복구되지 않는다.
    """
    op.add_column('video_evaluation_result', sa.Column('positive_rate', sa.Integer(), nullable=True))
    op.add_column('video_evaluation_result', sa.Column('neutral_rate', sa.Integer(), nullable=True))
    op.add_column('video_evaluation_result', sa.Column('negative_rate', sa.Integer(), nullable=True))
    op.add_column('video_evaluation_result', sa.Column('tense_rate', sa.Integer(), nullable=True))
    op.add_column('video_evaluation_result', sa.Column('emotion_best', sa.String(length=20), nullable=True))
    op.add_column('video_evaluation_result', sa.Column('emotion_score', sa.Integer(), nullable=True))
