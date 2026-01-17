"""add pixels_per_meter to planos

Revision ID: d8e9f0a1b2c3
Revises: c3d4e5f6g7h8
Create Date: 2026-01-17 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd8e9f0a1b2c3'
down_revision = 'c3d4e5f6g7h8'
branch_labels = None
depends_on = None


def upgrade():
    # Add pixels_per_meter column to planos table
    op.add_column('planos', sa.Column('pixels_per_meter', sa.Float(), nullable=True))


def downgrade():
    # Remove pixels_per_meter column from planos table
    op.drop_column('planos', 'pixels_per_meter')
