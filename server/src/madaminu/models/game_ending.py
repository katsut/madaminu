from sqlalchemy import JSON, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from madaminu.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class GameEnding(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "game_endings"

    game_id: Mapped[str] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), unique=True, nullable=False)
    ending_text: Mapped[str] = mapped_column(Text, nullable=False)
    criminal_epilogue: Mapped[str | None] = mapped_column(Text, nullable=True)
    true_criminal_id: Mapped[str] = mapped_column(ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    objective_results: Mapped[dict | None] = mapped_column(JSON, nullable=True)
