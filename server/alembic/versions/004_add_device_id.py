"""add device_id to players

Revision ID: 004
Revises: 003
Create Date: 2026-03-27
"""

from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("players", sa.Column("device_id", sa.String(36), nullable=True))
    op.create_index("ix_players_device_id", "players", ["device_id"])


def downgrade():
    op.drop_index("ix_players_device_id", "players")
    op.drop_column("players", "device_id")
