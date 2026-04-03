"""v3 initial schema - full rebuild

Revision ID: 001
Revises:
Create Date: 2026-03-31
"""

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: str | None = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- games ---
    op.create_table(
        "games",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("room_code", sa.String(6), nullable=False),
        sa.Column("room_name", sa.String(50), nullable=True),
        sa.Column("host_player_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="waiting"),
        sa.Column("current_phase_id", sa.String(), nullable=True),
        sa.Column("password", sa.String(100), nullable=True),
        sa.Column("template_id", sa.String(100), nullable=True),
        sa.Column("scenario_skeleton", sa.JSON(), nullable=True),
        sa.Column("gm_internal_state", sa.JSON(), nullable=True),
        sa.Column("scene_image", sa.Text(), nullable=True),
        sa.Column("victim_image", sa.Text(), nullable=True),
        sa.Column("total_llm_cost_usd", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("turn_count", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        # FK to players/phases are forward references — SQLAlchemy handles this
        # via use_alter in models; here we define them inline since tables are
        # created in one transaction.
    )
    op.create_index("ix_games_room_code", "games", ["room_code"], unique=True)

    # --- players ---
    op.create_table(
        "players",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("game_id", sa.String(), nullable=False),
        sa.Column("device_id", sa.String(36), nullable=True),
        sa.Column("session_token", sa.String(36), nullable=False),
        sa.Column("display_name", sa.String(50), nullable=False),
        sa.Column("character_name", sa.String(50), nullable=True),
        sa.Column("character_name_kana", sa.String(100), nullable=True),
        sa.Column("character_gender", sa.String(10), nullable=True),
        sa.Column("character_age", sa.String(10), nullable=True),
        sa.Column("character_occupation", sa.String(100), nullable=True),
        sa.Column("character_appearance", sa.Text(), nullable=True),
        sa.Column("character_personality", sa.Text(), nullable=True),
        sa.Column("character_background", sa.Text(), nullable=True),
        sa.Column("public_info", sa.Text(), nullable=True),
        sa.Column("secret_info", sa.Text(), nullable=True),
        sa.Column("objective", sa.Text(), nullable=True),
        sa.Column("role", sa.String(20), nullable=True),
        sa.Column("is_host", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_ai", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_ready", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_intro_ready", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("portrait_image", sa.Text(), nullable=True),
        sa.Column("connection_status", sa.String(20), nullable=False, server_default="offline"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_players_game_id", "players", ["game_id"])
    op.create_index("ix_players_device_id", "players", ["device_id"])
    op.create_index("ix_players_session_token", "players", ["session_token"], unique=True)

    # --- phases ---
    op.create_table(
        "phases",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("game_id", sa.String(), nullable=False),
        sa.Column("phase_type", sa.String(20), nullable=False),
        sa.Column("phase_order", sa.Integer(), nullable=False),
        sa.Column("duration_sec", sa.Integer(), nullable=False),
        sa.Column("scenario_update", sa.JSON(), nullable=True),
        sa.Column("investigation_locations", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("deadline_at", sa.DateTime(), nullable=True),
        sa.Column("paused_remaining_sec", sa.Integer(), nullable=True),
        sa.Column("current_speaker_id", sa.String(), nullable=True),
        sa.Column("discoveries_status", sa.String(20), nullable=False, server_default="pending"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_phases_game_id", "phases", ["game_id"])

    # --- notes ---
    op.create_table(
        "notes",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("player_id", sa.String(), nullable=False),
        sa.Column("game_id", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_notes_player_id", "notes", ["player_id"])

    # --- evidences ---
    op.create_table(
        "evidences",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("game_id", sa.String(), nullable=False),
        sa.Column("player_id", sa.String(), nullable=False),
        sa.Column("phase_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("revealed_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["phase_id"], ["phases.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_evidences_game_id", "evidences", ["game_id"])
    op.create_index("ix_evidences_player_id", "evidences", ["player_id"])

    # --- votes ---
    op.create_table(
        "votes",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("game_id", sa.String(), nullable=False),
        sa.Column("voter_player_id", sa.String(), nullable=False),
        sa.Column("suspect_player_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["voter_player_id"], ["players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["suspect_player_id"], ["players.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_votes_game_id", "votes", ["game_id"])

    # --- speech_logs ---
    op.create_table(
        "speech_logs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("game_id", sa.String(), nullable=False),
        sa.Column("player_id", sa.String(), nullable=False),
        sa.Column("phase_id", sa.String(), nullable=False),
        sa.Column("transcript", sa.Text(), nullable=False),
        sa.Column("corrected_transcript", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["phase_id"], ["phases.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_speech_logs_game_id", "speech_logs", ["game_id"])

    # --- game_endings ---
    op.create_table(
        "game_endings",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("game_id", sa.String(), nullable=False),
        sa.Column("ending_text", sa.Text(), nullable=False),
        sa.Column("criminal_epilogue", sa.Text(), nullable=True),
        sa.Column("true_criminal_id", sa.String(), nullable=False),
        sa.Column("objective_results", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["true_criminal_id"], ["players.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("game_id"),
    )

    # --- investigation_selections ---
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

    # --- payments ---
    op.create_table(
        "payments",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("game_id", sa.String(), nullable=False),
        sa.Column("player_id", sa.String(), nullable=False),
        sa.Column("receipt_data", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("payments")
    op.drop_table("investigation_selections")
    op.drop_table("game_endings")
    op.drop_table("speech_logs")
    op.drop_table("votes")
    op.drop_table("evidences")
    op.drop_table("notes")
    op.drop_table("phases")
    op.drop_table("players")
    op.drop_table("games")
