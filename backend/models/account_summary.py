from datetime import datetime

from sqlalchemy import Float, Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class AccountSummary(Base):
    __tablename__ = "account_summary"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    net_liquidation: Mapped[float | None] = mapped_column(Float)
    total_cash: Mapped[float | None] = mapped_column(Float)
    buying_power: Mapped[float | None] = mapped_column(Float)
    day_pnl: Mapped[float | None] = mapped_column(Float)
    unrealized_pnl: Mapped[float | None] = mapped_column(Float)
    realized_pnl: Mapped[float | None] = mapped_column(Float)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
