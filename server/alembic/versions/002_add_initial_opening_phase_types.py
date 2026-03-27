"""add initial and opening phase types

Revision ID: 002
Revises: 001
Create Date: 2026-03-27
"""

from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TYPE phasetype ADD VALUE IF NOT EXISTS 'initial' BEFORE 'planning'")
    op.execute("ALTER TYPE phasetype ADD VALUE IF NOT EXISTS 'opening' BEFORE 'planning'")


def downgrade():
    pass
