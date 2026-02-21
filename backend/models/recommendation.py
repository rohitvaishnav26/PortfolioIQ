from datetime import datetime

from sqlalchemy import Float, Integer, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)   # BUY, ADD, TRIM, SELL, HOLD, WATCH
    urgency: Mapped[str] = mapped_column(String, nullable=False)  # high, medium, low
    suggested_size_pct: Mapped[float | None] = mapped_column(Float)
    suggested_tranche: Mapped[int | None] = mapped_column(Integer)
    total_tranches: Mapped[int | None] = mapped_column(Integer)
    timing_note: Mapped[str | None] = mapped_column(Text)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    conflicting_signals: Mapped[str | None] = mapped_column(Text)   # JSON array
    supporting_strategies: Mapped[str | None] = mapped_column(Text) # JSON array
    risk_factors: Mapped[str | None] = mapped_column(Text)          # JSON array
    model_used: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
