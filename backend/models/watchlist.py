from datetime import datetime

from sqlalchemy import Boolean, Float, Integer, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class Watchlist(Base):
    __tablename__ = "watchlist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    notes: Mapped[str | None] = mapped_column(Text)
    target_price: Mapped[float | None] = mapped_column(Float)
    alert_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
