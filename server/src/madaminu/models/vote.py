from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from madaminu.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from madaminu.models.game import Game


class Vote(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "votes"

    game_id: Mapped[str] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True)
    voter_player_id: Mapped[str] = mapped_column(ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    suspect_player_id: Mapped[str] = mapped_column(ForeignKey("players.id", ondelete="CASCADE"), nullable=False)

    game: Mapped[Game] = relationship("Game", back_populates="votes")
