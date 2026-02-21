from datetime import date, datetime

from sqlalchemy import Date, Float, Integer, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    account: Mapped[str] = mapped_column(String, nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    settle_date: Mapped[date | None] = mapped_column(Date)
    action: Mapped[str] = mapped_column(String, nullable=False)  # BUY, SELL, DIV, SPLIT, etc.
    shares: Mapped[float | None] = mapped_column(Float)
    price: Mapped[float | None] = mapped_column(Float)
    commission: Mapped[float] = mapped_column(Float, default=0)
    amount: Mapped[float] = mapped_column(Float, nullable=False)  # net cash impact
    description: Mapped[str | None] = mapped_column(Text)
    ibkr_trade_id: Mapped[str | None] = mapped_column(String, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
