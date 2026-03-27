"""add ondelete CASCADE to all foreign keys

Revision ID: 008
Revises: 007
Create Date: 2026-03-27
"""

from alembic import op

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None

FK_UPDATES = [
    ("players", "players_game_id_fkey", "game_id", "games.id"),
    ("phases", "phases_game_id_fkey", "game_id", "games.id"),
    ("speech_logs", "speech_logs_game_id_fkey", "game_id", "games.id"),
    ("speech_logs", "speech_logs_player_id_fkey", "player_id", "players.id"),
    ("speech_logs", "speech_logs_phase_id_fkey", "phase_id", "phases.id"),
    ("evidences", "evidences_game_id_fkey", "game_id", "games.id"),
    ("evidences", "evidences_player_id_fkey", "player_id", "players.id"),
    ("evidences", "evidences_phase_id_fkey", "phase_id", "phases.id"),
    ("votes", "votes_game_id_fkey", "game_id", "games.id"),
    ("votes", "votes_voter_player_id_fkey", "voter_player_id", "players.id"),
    ("votes", "votes_suspect_player_id_fkey", "suspect_player_id", "players.id"),
    ("notes", "notes_player_id_fkey", "player_id", "players.id"),
    ("notes", "notes_game_id_fkey", "game_id", "games.id"),
    ("payments", "payments_game_id_fkey", "game_id", "games.id"),
    ("payments", "payments_player_id_fkey", "player_id", "players.id"),
    ("game_endings", "game_endings_game_id_fkey", "game_id", "games.id"),
    ("game_endings", "game_endings_true_criminal_id_fkey", "true_criminal_id", "players.id"),
]


def upgrade():
    for table, fk_name, column, ref in FK_UPDATES:
        op.drop_constraint(fk_name, table, type_="foreignkey")
        op.create_foreign_key(fk_name, table, ref.split(".")[0], [column], ["id"], ondelete="CASCADE")


def downgrade():
    for table, fk_name, column, ref in FK_UPDATES:
        op.drop_constraint(fk_name, table, type_="foreignkey")
        op.create_foreign_key(fk_name, table, ref.split(".")[0], [column], ["id"])
