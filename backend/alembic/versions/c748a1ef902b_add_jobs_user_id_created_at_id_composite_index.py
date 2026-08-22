"""add_jobs_user_id_created_at_id_composite_index

Revision ID: c748a1ef902b
Revises: a959a0f88633
Create Date: 2026-08-22 17:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c748a1ef902b'
down_revision: Union[str, Sequence[str], None] = 'a959a0f88633'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index('ix_jobs_user_id_created_at_id', 'jobs', ['user_id', 'created_at', 'id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_jobs_user_id_created_at_id', table_name='jobs')
