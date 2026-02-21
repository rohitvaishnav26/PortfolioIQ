from datetime import datetime

from sqlalchemy import Float, Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class Fundamentals(Base):
    __tablename__ = "fundamentals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    # Value metrics
    pe_ratio: Mapped[float | None] = mapped_column(Float)
    pb_ratio: Mapped[float | None] = mapped_column(Float)
    ev_ebitda: Mapped[float | None] = mapped_column(Float)
    fcf_yield: Mapped[float | None] = mapped_column(Float)
    # Quality / profitability
    roe: Mapped[float | None] = mapped_column(Float)
    roic: Mapped[float | None] = mapped_column(Float)
    debt_equity: Mapped[float | None] = mapped_column(Float)
    gross_margin: Mapped[float | None] = mapped_column(Float)
    fcf_margin: Mapped[float | None] = mapped_column(Float)
    # Growth
    revenue_cagr_3y: Mapped[float | None] = mapped_column(Float)
    eps_cagr_3y: Mapped[float | None] = mapped_column(Float)
    revenue_cagr_5y: Mapped[float | None] = mapped_column(Float)
    eps_growth_5y: Mapped[float | None] = mapped_column(Float)
    peg_ratio: Mapped[float | None] = mapped_column(Float)
    # Income
    dividend_yield: Mapped[float | None] = mapped_column(Float)
    payout_ratio: Mapped[float | None] = mapped_column(Float)
    dividend_cagr_5y: Mapped[float | None] = mapped_column(Float)
    consecutive_div_growth_years: Mapped[int | None] = mapped_column(Integer)
    earnings_coverage_ratio: Mapped[float | None] = mapped_column(Float)
    # Classification
    sector: Mapped[str | None] = mapped_column(String)
    industry: Mapped[str | None] = mapped_column(String)
    sector_pe_median: Mapped[float | None] = mapped_column(Float)
    sector_ev_ebitda_median: Mapped[float | None] = mapped_column(Float)
    # Cache control
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
