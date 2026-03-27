from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from madaminu.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from madaminu.models.game import Game


class SpeechLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "speech_logs"

    game_id: Mapped[str] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True)
    player_id: Mapped[str] = mapped_column(ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    phase_id: Mapped[str] = mapped_column(ForeignKey("phases.id", ondelete="CASCADE"), nullable=False)
    transcript: Mapped[str] = mapped_column(Text, nullable=False)
    corrected_transcript: Mapped[str | None] = mapped_column(Text, nullable=True)

    game: Mapped[Game] = relationship("Game", back_populates="speech_logs")
