from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from madaminu.models.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from madaminu.models.player import Player


class Note(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "notes"

    player_id: Mapped[str] = mapped_column(ForeignKey("players.id"), nullable=False, index=True)
    game_id: Mapped[str] = mapped_column(ForeignKey("games.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    updated_at: Mapped[str] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    player: Mapped[Player] = relationship("Player", back_populates="notes")
