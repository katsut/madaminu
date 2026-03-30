"""add discovery to evidencesource enum

Revision ID: add_discovery
Revises: ff73e85ff97b
Create Date: 2026-03-30
"""

from alembic import op

revision = "add_discovery"
down_revision = "ff73e85ff97b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE evidencesource ADD VALUE IF NOT EXISTS 'discovery'")


def downgrade() -> None:
    pass
