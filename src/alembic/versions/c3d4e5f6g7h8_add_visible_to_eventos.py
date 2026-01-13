"""Add visible column to eventos table

Revision ID: c3d4e5f6g7h8
Revises: a1b2c3d4e5f6
Create Date: 2026-01-12

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c3d4e5f6g7h8'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('eventos', sa.Column('visible', sa.Boolean(), nullable=False, server_default='true'))


def downgrade():
    op.drop_column('eventos', 'visible')
