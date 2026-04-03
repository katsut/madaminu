from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from madaminu.models.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from madaminu.models.game import Game


class PhaseType(enum.StrEnum):
    initial = "initial"
    storytelling = "storytelling"
    opening = "opening"
    briefing = "briefing"
    discussion = "discussion"
    planning = "planning"
    investigation = "investigation"
    voting = "voting"


class Phase(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "phases"

    game_id: Mapped[str] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True)
    phase_type: Mapped[PhaseType] = mapped_column(Enum(PhaseType), nullable=False)
    phase_order: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_sec: Mapped[int] = mapped_column(Integer, nullable=False)
    scenario_update: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    investigation_locations: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[str | None] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[str | None] = mapped_column(DateTime, nullable=True)
    deadline_at: Mapped[str | None] = mapped_column(DateTime, nullable=True)
    paused_remaining_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_speaker_id: Mapped[str | None] = mapped_column(ForeignKey("players.id", use_alter=True), nullable=True)
    discoveries_status: Mapped[str] = mapped_column(String(20), server_default="pending", nullable=False)

    game: Mapped[Game] = relationship("Game", back_populates="phases", foreign_keys=[game_id])
