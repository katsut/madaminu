import enum

from sqlalchemy import DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from madaminu.models.base import Base, UUIDPrimaryKeyMixin


class PaymentStatus(enum.StrEnum):
    pending = "pending"
    verified = "verified"
    failed = "failed"


class Payment(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "payments"

    game_id: Mapped[str] = mapped_column(ForeignKey("games.id"), nullable=False)
    player_id: Mapped[str] = mapped_column(ForeignKey("players.id"), nullable=False)
    receipt_data: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), default=PaymentStatus.pending, nullable=False)
    verified_at: Mapped[str | None] = mapped_column(DateTime, nullable=True)
