from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from madaminu.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from madaminu.models.evidence import Evidence
    from madaminu.models.game import Game
    from madaminu.models.note import Note


class PlayerRole(enum.StrEnum):
    criminal = "criminal"
    witness = "witness"
    related = "related"
    innocent = "innocent"


class ConnectionStatus(enum.StrEnum):
    online = "online"
    offline = "offline"


class Player(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "players"

    game_id: Mapped[str] = mapped_column(ForeignKey("games.id"), nullable=False, index=True)
    session_token: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(50), nullable=False)
    character_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    character_personality: Mapped[str | None] = mapped_column(Text, nullable=True)
    character_background: Mapped[str | None] = mapped_column(Text, nullable=True)
    secret_info: Mapped[str | None] = mapped_column(Text, nullable=True)
    objective: Mapped[str | None] = mapped_column(Text, nullable=True)
    role: Mapped[PlayerRole | None] = mapped_column(Enum(PlayerRole), nullable=True)
    is_host: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    connection_status: Mapped[ConnectionStatus] = mapped_column(
        Enum(ConnectionStatus), default=ConnectionStatus.offline, nullable=False
    )

    game: Mapped[Game] = relationship("Game", back_populates="players", foreign_keys=[game_id])
    notes: Mapped[list[Note]] = relationship("Note", back_populates="player")
    evidences: Mapped[list[Evidence]] = relationship("Evidence", back_populates="player")
