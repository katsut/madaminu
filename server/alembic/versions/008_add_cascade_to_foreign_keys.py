"""add ondelete CASCADE to all foreign keys

Revision ID: 008
Revises: 007
Create Date: 2026-03-27
"""

from alembic import op
from sqlalchemy import inspect, text

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None

TABLES_TO_UPDATE = [
    "players",
    "phases",
    "speech_logs",
    "evidences",
    "votes",
    "notes",
    "payments",
    "game_endings",
]


def upgrade():
    conn = op.get_bind()
    for table in TABLES_TO_UPDATE:
        inspector = inspect(conn)
        fks = inspector.get_foreign_keys(table)
        for fk in fks:
            fk_name = fk["name"]
            if fk_name is None:
                continue
            constrained = fk["constrained_columns"]
            referred_table = fk["referred_table"]
            referred_columns = fk["referred_columns"]
            op.drop_constraint(fk_name, table, type_="foreignkey")
            op.create_foreign_key(
                fk_name, table, referred_table,
                constrained, referred_columns,
                ondelete="CASCADE",
            )


def downgrade():
    conn = op.get_bind()
    for table in TABLES_TO_UPDATE:
        inspector = inspect(conn)
        fks = inspector.get_foreign_keys(table)
        for fk in fks:
            fk_name = fk["name"]
            if fk_name is None:
                continue
            constrained = fk["constrained_columns"]
            referred_table = fk["referred_table"]
            referred_columns = fk["referred_columns"]
            op.drop_constraint(fk_name, table, type_="foreignkey")
            op.create_foreign_key(
                fk_name, table, referred_table,
                constrained, referred_columns,
            )
