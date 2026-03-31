"""v3 schema extensions: investigation_selections, phase/player columns, storytelling phase type

Revision ID: v3_schema
Revises: add_discovery
Create Date: 2026-03-31
"""

import sqlalchemy as sa
from alembic import op

revision = "v3_schema"
down_revision = "add_discovery"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PhaseType: add storytelling
    op.execute("ALTER TYPE phasetype ADD VALUE IF NOT EXISTS 'storytelling'")

    # New table: investigation_selections
    op.create_table(
        "investigation_selections",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("game_id", sa.String(), nullable=False),
        sa.Column("phase_id", sa.String(), nullable=False),
        sa.Column("player_id", sa.String(), nullable=False),
        sa.Column("location_id", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["phase_id"], ["phases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("phase_id", "player_id"),
    )
    op.create_index("ix_investigation_selections_game_id", "investigation_selections", ["game_id"])
    op.create_index("ix_investigation_selections_phase_id", "investigation_selections", ["phase_id"])
    op.create_index("ix_investigation_selections_player_id", "investigation_selections", ["player_id"])

    # Phase table extensions
    op.add_column("phases", sa.Column("paused_remaining_sec", sa.Integer(), nullable=True))
    op.add_column("phases", sa.Column("current_speaker_id", sa.String(), nullable=True))
    op.add_column("phases", sa.Column("discoveries_status", sa.String(20), server_default="pending", nullable=False))

    # Player table extension
    op.add_column("players", sa.Column("is_intro_ready", sa.Boolean(), server_default="false", nullable=False))


def downgrade() -> None:
    op.drop_column("players", "is_intro_ready")
    op.drop_column("phases", "discoveries_status")
    op.drop_column("phases", "current_speaker_id")
    op.drop_column("phases", "paused_remaining_sec")
    op.drop_table("investigation_selections")
