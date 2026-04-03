from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from madaminu.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class InvestigationSelection(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "investigation_selections"
    __table_args__ = (UniqueConstraint("phase_id", "player_id"),)

    game_id: Mapped[str] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True)
    phase_id: Mapped[str] = mapped_column(ForeignKey("phases.id", ondelete="CASCADE"), nullable=False, index=True)
    player_id: Mapped[str] = mapped_column(ForeignKey("players.id", ondelete="CASCADE"), nullable=False, index=True)
    location_id: Mapped[str] = mapped_column(String(100), nullable=False)
