from datetime import datetime

from sqlalchemy import CheckConstraint, Integer, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class Signal(Base):
    __tablename__ = "signals"
    __table_args__ = (CheckConstraint("confidence BETWEEN 0 AND 100", name="ck_signal_confidence"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    strategy: Mapped[str] = mapped_column(String, nullable=False)  # momentum, value, growth, etc.
    signal: Mapped[str] = mapped_column(String, nullable=False)    # BUY, SELL, HOLD
    confidence: Mapped[int] = mapped_column(Integer, nullable=False)
    reasoning: Mapped[str | None] = mapped_column(Text)
    key_metrics: Mapped[str | None] = mapped_column(Text)  # JSON blob
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)
