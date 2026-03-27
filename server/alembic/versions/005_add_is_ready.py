"""add is_ready to players

Revision ID: 005
Revises: 004
Create Date: 2026-03-27
"""

from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("players", sa.Column("is_ready", sa.Boolean(), nullable=False, server_default="false"))


def downgrade():
    op.drop_column("players", "is_ready")
