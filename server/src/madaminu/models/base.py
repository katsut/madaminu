import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class UUIDPrimaryKeyMixin:
    id: Mapped[str] = mapped_column(primary_key=True, default=lambda: str(uuid.uuid4()))
