"""add turn_count to games and planning phase type

Revision ID: 007
Revises: 006
Create Date: 2026-03-27
"""

from alembic import op
import sqlalchemy as sa

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("games", sa.Column("turn_count", sa.Integer(), nullable=False, server_default="3"))


def downgrade():
    op.drop_column("games", "turn_count")
