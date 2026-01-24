"""add rotation to polygons

Revision ID: e9f0a1b2c3d4
Revises: d8e9f0a1b2c3
Create Date: 2026-01-24 18:10:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "e9f0a1b2c3d4"
down_revision = "d8e9f0a1b2c3"
branch_labels = None
depends_on = None


def upgrade():
    # Add rotation column to polygons table (for stand/zone rotation in degrees)
    op.add_column("polygons", sa.Column("rotation", sa.Numeric(5, 2), nullable=False, server_default="0"))


def downgrade():
    # Remove rotation column from polygons table
    op.drop_column("polygons", "rotation")
