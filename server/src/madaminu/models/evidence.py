from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from madaminu.models.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from madaminu.models.player import Player


class EvidenceSource(enum.StrEnum):
    investigation = "investigation"
    gm_push = "gm_push"


class Evidence(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "evidences"

    game_id: Mapped[str] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True)
    player_id: Mapped[str] = mapped_column(ForeignKey("players.id", ondelete="CASCADE"), nullable=False, index=True)
    phase_id: Mapped[str] = mapped_column(ForeignKey("phases.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[EvidenceSource] = mapped_column(Enum(EvidenceSource), nullable=False)
    revealed_at: Mapped[str] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    player: Mapped[Player] = relationship("Player", back_populates="evidences")
