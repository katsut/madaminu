"""add character_name_kana and public_info to players

Revision ID: 006
Revises: 005
Create Date: 2026-03-27
"""

from alembic import op
import sqlalchemy as sa

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("players", sa.Column("character_name_kana", sa.String(100), nullable=True))
    op.add_column("players", sa.Column("public_info", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("players", "public_info")
    op.drop_column("players", "character_name_kana")
