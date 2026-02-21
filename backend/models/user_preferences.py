from datetime import datetime

from sqlalchemy import Boolean, Float, Integer, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)  # single row
    investment_horizon: Mapped[str] = mapped_column(String, default="long")       # short, medium, long
    risk_tolerance: Mapped[str] = mapped_column(String, default="moderate")       # conservative, moderate, aggressive
    max_single_position_pct: Mapped[float] = mapped_column(Float, default=10.0)
    max_sector_pct: Mapped[float] = mapped_column(Float, default=25.0)
    preferred_strategies: Mapped[str] = mapped_column(
        Text, default='["quality","long_term","growth"]'
    )  # JSON array
    hybrid_profiles: Mapped[str] = mapped_column(Text, default="[]")  # JSON array of HybridProfile objects
    tax_sensitive: Mapped[bool] = mapped_column(Boolean, default=False)
    min_confidence_to_act: Mapped[int] = mapped_column(Integer, default=60)
    scale_in_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    scale_in_tranches: Mapped[int] = mapped_column(Integer, default=3)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
