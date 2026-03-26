"""initial

Revision ID: 001
Revises:
Create Date: 2026-03-26
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "games",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("room_code", sa.String(6), nullable=False),
        sa.Column("host_player_id", sa.String(), nullable=True),
        sa.Column("status", sa.Enum("waiting", "generating", "playing", "voting", "ended", name="gamestatus"), nullable=False),
        sa.Column("current_phase_id", sa.String(), nullable=True),
        sa.Column("password", sa.String(100), nullable=True),
        sa.Column("template_id", sa.String(100), nullable=True),
        sa.Column("scenario_skeleton", sa.JSON(), nullable=True),
        sa.Column("gm_internal_state", sa.JSON(), nullable=True),
        sa.Column("scene_image", sa.Text(), nullable=True),
        sa.Column("victim_image", sa.Text(), nullable=True),
        sa.Column("total_llm_cost_usd", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_games_room_code", "games", ["room_code"], unique=True)

    op.create_table(
        "players",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("game_id", sa.String(), nullable=False),
        sa.Column("session_token", sa.String(36), nullable=False),
        sa.Column("display_name", sa.String(50), nullable=False),
        sa.Column("character_name", sa.String(50), nullable=True),
        sa.Column("character_personality", sa.Text(), nullable=True),
        sa.Column("character_background", sa.Text(), nullable=True),
        sa.Column("secret_info", sa.Text(), nullable=True),
        sa.Column("objective", sa.Text(), nullable=True),
        sa.Column("role", sa.Enum("criminal", "witness", "related", "innocent", name="playerrole"), nullable=True),
        sa.Column("is_host", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_ai", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("portrait_image", sa.Text(), nullable=True),
        sa.Column("connection_status", sa.Enum("online", "offline", name="connectionstatus"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_players_game_id", "players", ["game_id"])
    op.create_index("ix_players_session_token", "players", ["session_token"], unique=True)

    op.create_table(
        "phases",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("game_id", sa.String(), nullable=False),
        sa.Column("phase_type", sa.Enum("investigation", "discussion", "voting", name="phasetype"), nullable=False),
        sa.Column("phase_order", sa.Integer(), nullable=False),
        sa.Column("duration_sec", sa.Integer(), nullable=False),
        sa.Column("scenario_update", sa.JSON(), nullable=True),
        sa.Column("investigation_locations", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("deadline_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_phases_game_id", "phases", ["game_id"])

    # Add FKs on games that reference players and phases
    op.create_foreign_key("fk_games_host_player_id", "games", "players", ["host_player_id"], ["id"], use_alter=True)
    op.create_foreign_key("fk_games_current_phase_id", "games", "phases", ["current_phase_id"], ["id"], use_alter=True)

    op.create_table(
        "speech_logs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("game_id", sa.String(), nullable=False),
        sa.Column("player_id", sa.String(), nullable=False),
        sa.Column("phase_id", sa.String(), nullable=False),
        sa.Column("transcript", sa.Text(), nullable=False),
        sa.Column("corrected_transcript", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"]),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"]),
        sa.ForeignKeyConstraint(["phase_id"], ["phases.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_speech_logs_game_id", "speech_logs", ["game_id"])

    op.create_table(
        "votes",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("game_id", sa.String(), nullable=False),
        sa.Column("voter_player_id", sa.String(), nullable=False),
        sa.Column("suspect_player_id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"]),
        sa.ForeignKeyConstraint(["voter_player_id"], ["players.id"]),
        sa.ForeignKeyConstraint(["suspect_player_id"], ["players.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_votes_game_id", "votes", ["game_id"])

    op.create_table(
        "evidences",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("game_id", sa.String(), nullable=False),
        sa.Column("player_id", sa.String(), nullable=False),
        sa.Column("phase_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source", sa.Enum("investigation", "gm_push", name="evidencesource"), nullable=False),
        sa.Column("revealed_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"]),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"]),
        sa.ForeignKeyConstraint(["phase_id"], ["phases.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_evidences_game_id", "evidences", ["game_id"])
    op.create_index("ix_evidences_player_id", "evidences", ["player_id"])

    op.create_table(
        "game_endings",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("game_id", sa.String(), nullable=False),
        sa.Column("ending_text", sa.Text(), nullable=False),
        sa.Column("true_criminal_id", sa.String(), nullable=False),
        sa.Column("objective_results", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"]),
        sa.ForeignKeyConstraint(["true_criminal_id"], ["players.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("game_id"),
    )

    op.create_table(
        "notes",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("player_id", sa.String(), nullable=False),
        sa.Column("game_id", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"]),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notes_player_id", "notes", ["player_id"])

    op.create_table(
        "payments",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("game_id", sa.String(), nullable=False),
        sa.Column("player_id", sa.String(), nullable=False),
        sa.Column("receipt_data", sa.Text(), nullable=False),
        sa.Column("status", sa.Enum("pending", "verified", "failed", name="paymentstatus"), nullable=False),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"]),
        sa.ForeignKeyConstraint(["player_id"], ["players.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("payments")
    op.drop_table("notes")
    op.drop_table("game_endings")
    op.drop_table("evidences")
    op.drop_table("votes")
    op.drop_table("speech_logs")
    op.drop_constraint("fk_games_current_phase_id", "games", type_="foreignkey")
    op.drop_constraint("fk_games_host_player_id", "games", type_="foreignkey")
    op.drop_table("phases")
    op.drop_table("players")
    op.drop_table("games")
