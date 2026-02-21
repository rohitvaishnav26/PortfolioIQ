from datetime import datetime

from sqlalchemy import Integer, String, Text, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class ResearchCache(Base):
    __tablename__ = "research_cache"
    __table_args__ = (UniqueConstraint("symbol", "briefing_type"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    briefing_type: Mapped[str] = mapped_column(String, nullable=False)  # holding_brief, watchlist_analysis
    content: Mapped[str] = mapped_column(Text, nullable=False)          # full markdown briefing
    model: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
