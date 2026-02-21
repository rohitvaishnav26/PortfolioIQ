"""Shared pytest fixtures for PortfolioIQ test suite."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="function")
async def async_engine():
    """In-memory SQLite engine with all tables created."""
    from backend.models.base import Base  # noqa: PLC0415

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Async session scoped to each test; rolls back on teardown."""
    session_factory = async_sessionmaker(async_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


# ---------------------------------------------------------------------------
# FastAPI test client
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="function")
async def test_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """FastAPI AsyncClient with DB dependency overridden to use test session."""
    from backend.database import get_session  # noqa: PLC0415
    from backend.main import app  # noqa: PLC0415

    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Seeded data fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="function")
async def sample_position(db_session: AsyncSession):
    """Insert a Position row for symbol 'TEST' and return it."""
    from backend.models.position import Position  # noqa: PLC0415

    position = Position(
        symbol="TEST",
        account="U1234567",
        shares=100.0,
        avg_cost=50.0,
        current_price=55.0,
        market_value=5500.0,
        unrealized_pnl=500.0,
        unrealized_pnl_pct=10.0,
        realized_pnl=0.0,
        sector="Technology",
        industry="Software",
        last_updated=datetime.now(timezone.utc),
    )
    db_session.add(position)
    await db_session.commit()
    await db_session.refresh(position)
    return position


@pytest_asyncio.fixture(scope="function")
async def sample_fundamentals(db_session: AsyncSession):
    """Insert a Fundamentals row for symbol 'TEST' and return it."""
    from backend.models.fundamentals import Fundamentals  # noqa: PLC0415

    fundamentals = Fundamentals(
        symbol="TEST",
        pe_ratio=15.0,
        pb_ratio=2.0,
        ev_ebitda=10.0,
        fcf_yield=6.0,
        roe=18.0,
        roic=14.0,
        debt_equity=0.3,
        gross_margin=45.0,
        dividend_yield=2.0,
        payout_ratio=35.0,
        eps_growth_5y=12.0,
        dividend_cagr_5y=8.0,
        consecutive_div_growth_years=7,
        sector="Technology",
        industry="Software",
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(fundamentals)
    await db_session.commit()
    await db_session.refresh(fundamentals)
    return fundamentals


# ---------------------------------------------------------------------------
# External service mocks
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def mock_yfinance_ticker():
    """Patch yfinance.Ticker with canned OHLCV history and info dict."""
    dates = pd.date_range(end=pd.Timestamp.today(), periods=252, freq="B")
    # Gently uptrending price series
    closes = [100.0 + i * 0.1 for i in range(252)]
    ohlcv = pd.DataFrame(
        {
            "Open": closes,
            "High": [c + 1 for c in closes],
            "Low": [c - 1 for c in closes],
            "Close": closes,
            "Volume": [1_000_000] * 252,
        },
        index=dates,
    )
    info = {
        "currentPrice": 125.10,
        "regularMarketChangePercent": 0.85,
        "regularMarketVolume": 1_200_000,
        "trailingPE": 15.0,
        "priceToBook": 2.0,
        "enterpriseToEbitda": 10.0,
        "freeCashflow": 5_000_000,
        "marketCap": 80_000_000,
        "returnOnEquity": 0.18,
        "debtToEquity": 30.0,
        "grossMargins": 0.45,
        "dividendYield": 0.02,
        "payoutRatio": 0.35,
        "sector": "Technology",
        "industry": "Software",
    }
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = ohlcv
    mock_ticker.fast_info = MagicMock(
        last_price=info["currentPrice"],
        last_volume=info["regularMarketVolume"],
    )
    mock_ticker.info = info

    with patch("yfinance.Ticker", return_value=mock_ticker) as mock_cls:
        yield mock_cls


@pytest.fixture(scope="function")
def mock_claude_response():
    """AsyncMock returning a valid SmartRecommendation JSON payload."""
    recommendation_json = {
        "symbol": "TEST",
        "action": "HOLD",
        "urgency": "low",
        "suggested_size_pct": 0.0,
        "suggested_tranche": 1,
        "total_tranches": 1,
        "timing_note": "No action required at this time.",
        "rationale": "Quality fundamentals with no clear catalyst. Maintain current position.",
        "conflicting_signals": [],
        "risk_factors": ["Macro uncertainty"],
        "supporting_strategies": ["quality", "long_term"],
    }
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=json.dumps(recommendation_json))]

    mock_create = AsyncMock(return_value=mock_response)
    with patch(
        "anthropic.AsyncAnthropic.messages.create", new=mock_create
    ):
        yield mock_create
