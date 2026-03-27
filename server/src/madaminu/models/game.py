from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from madaminu.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from madaminu.models.phase import Phase
    from madaminu.models.player import Player
    from madaminu.models.speech_log import SpeechLog
    from madaminu.models.vote import Vote


class GameStatus(enum.StrEnum):
    waiting = "waiting"
    generating = "generating"
    playing = "playing"
    voting = "voting"
    ended = "ended"


class Game(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "games"

    room_code: Mapped[str] = mapped_column(String(6), unique=True, nullable=False, index=True)
    host_player_id: Mapped[str | None] = mapped_column(ForeignKey("players.id", use_alter=True), nullable=True)
    status: Mapped[GameStatus] = mapped_column(Enum(GameStatus), default=GameStatus.waiting, nullable=False)
    current_phase_id: Mapped[str | None] = mapped_column(ForeignKey("phases.id", use_alter=True), nullable=True)
    password: Mapped[str | None] = mapped_column(String(100), nullable=True)
    template_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    scenario_skeleton: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    gm_internal_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    scene_image: Mapped[str | None] = mapped_column(Text, nullable=True)
    victim_image: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_llm_cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    turn_count: Mapped[int] = mapped_column(Integer, default=3, server_default="3", nullable=False)
    updated_at: Mapped[str | None] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    players: Mapped[list[Player]] = relationship("Player", back_populates="game", foreign_keys="Player.game_id", cascade="all, delete-orphan", passive_deletes=True)
    phases: Mapped[list[Phase]] = relationship("Phase", back_populates="game", foreign_keys="Phase.game_id", cascade="all, delete-orphan", passive_deletes=True)
    speech_logs: Mapped[list[SpeechLog]] = relationship("SpeechLog", back_populates="game", cascade="all, delete-orphan", passive_deletes=True)
    votes: Mapped[list[Vote]] = relationship("Vote", back_populates="game", cascade="all, delete-orphan", passive_deletes=True)
