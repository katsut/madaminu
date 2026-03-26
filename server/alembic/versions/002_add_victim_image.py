"""add victim_image column

Revision ID: 002
Revises: 001
Create Date: 2026-03-26
"""

from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("games", sa.Column("victim_image", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("games", "victim_image")
