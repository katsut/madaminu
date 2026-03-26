"""add character profile fields

Revision ID: 003
Revises: 002
Create Date: 2026-03-26
"""

from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("players", sa.Column("character_gender", sa.String(10), nullable=True))
    op.add_column("players", sa.Column("character_age", sa.String(10), nullable=True))
    op.add_column("players", sa.Column("character_occupation", sa.String(100), nullable=True))
    op.add_column("players", sa.Column("character_appearance", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("players", "character_appearance")
    op.drop_column("players", "character_occupation")
    op.drop_column("players", "character_age")
    op.drop_column("players", "character_gender")
