"""TASK-003: Smoke tests — import all models and basic CRUD for each table."""

from __future__ import annotations

from datetime import date, datetime, timezone


# ---------------------------------------------------------------------------
# Smoke: all models importable
# ---------------------------------------------------------------------------

def test_all_models_importable():
    from backend.models import (  # noqa: F401
        AccountSummary,
        Base,
        Fundamentals,
        MarketData,
        Position,
        Recommendation,
        ResearchCache,
        Signal,
        SyncLog,
        Transaction,
        UserPreferences,
        Watchlist,
    )


# ---------------------------------------------------------------------------
# Position
# ---------------------------------------------------------------------------

async def test_position_crud(db_session):
    from sqlalchemy import select

    from backend.models.position import Position

    pos = Position(
        symbol="AAPL",
        account="U1234567",
        shares=50.0,
        avg_cost=150.0,
        current_price=175.0,
        market_value=8750.0,
        unrealized_pnl=1250.0,
        unrealized_pnl_pct=16.67,
        realized_pnl=0.0,
        sector="Technology",
        industry="Consumer Electronics",
        last_updated=datetime.now(timezone.utc),
    )
    db_session.add(pos)
    await db_session.commit()

    result = await db_session.execute(select(Position).where(Position.symbol == "AAPL"))
    fetched = result.scalar_one()

    assert fetched.symbol == "AAPL"
    assert fetched.account == "U1234567"
    assert fetched.shares == 50.0
    assert fetched.avg_cost == 150.0
    assert fetched.sector == "Technology"


# ---------------------------------------------------------------------------
# Transaction
# ---------------------------------------------------------------------------

async def test_transaction_crud(db_session):
    from sqlalchemy import select

    from backend.models.transaction import Transaction

    txn = Transaction(
        symbol="MSFT",
        account="U1234567",
        trade_date=date(2025, 1, 15),
        action="BUY",
        shares=10.0,
        price=400.0,
        commission=1.0,
        amount=-4001.0,
        ibkr_trade_id="TRD-001",
    )
    db_session.add(txn)
    await db_session.commit()

    result = await db_session.execute(select(Transaction).where(Transaction.symbol == "MSFT"))
    fetched = result.scalar_one()

    assert fetched.action == "BUY"
    assert fetched.shares == 10.0
    assert fetched.ibkr_trade_id == "TRD-001"


# ---------------------------------------------------------------------------
# MarketData
# ---------------------------------------------------------------------------

async def test_market_data_crud(db_session):
    from sqlalchemy import select

    from backend.models.market_data import MarketData

    row = MarketData(
        symbol="SPY",
        date=date(2025, 6, 1),
        open=530.0,
        high=535.0,
        low=528.0,
        close=533.0,
        volume=80_000_000,
        adj_close=533.0,
    )
    db_session.add(row)
    await db_session.commit()

    result = await db_session.execute(
        select(MarketData).where(MarketData.symbol == "SPY", MarketData.date == date(2025, 6, 1))
    )
    fetched = result.scalar_one()

    assert fetched.close == 533.0
    assert fetched.volume == 80_000_000


# ---------------------------------------------------------------------------
# Fundamentals
# ---------------------------------------------------------------------------

async def test_fundamentals_crud(db_session):
    from sqlalchemy import select

    from backend.models.fundamentals import Fundamentals

    fund = Fundamentals(
        symbol="GOOG",
        pe_ratio=22.0,
        fcf_yield=5.5,
        roe=25.0,
        roic=20.0,
        debt_equity=0.1,
        gross_margin=55.0,
        sector="Communication Services",
        industry="Internet Content",
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(fund)
    await db_session.commit()

    result = await db_session.execute(select(Fundamentals).where(Fundamentals.symbol == "GOOG"))
    fetched = result.scalar_one()

    assert fetched.symbol == "GOOG"
    assert fetched.pe_ratio == 22.0
    assert fetched.gross_margin == 55.0


# ---------------------------------------------------------------------------
# Signal
# ---------------------------------------------------------------------------

async def test_signal_crud(db_session):
    from sqlalchemy import select

    from backend.models.signal import Signal

    sig = Signal(
        symbol="NVDA",
        strategy="momentum",
        signal="BUY",
        confidence=82,
        reasoning="Strong uptrend with RSI in range",
        key_metrics='{"rsi": 58, "macd_cross": true}',
    )
    db_session.add(sig)
    await db_session.commit()

    result = await db_session.execute(
        select(Signal).where(Signal.strategy == "momentum", Signal.symbol == "NVDA")
    )
    fetched = result.scalar_one()

    assert fetched.signal == "BUY"
    assert fetched.confidence == 82


# ---------------------------------------------------------------------------
# AccountSummary
# ---------------------------------------------------------------------------

async def test_account_summary_crud(db_session):
    from sqlalchemy import select

    from backend.models.account_summary import AccountSummary

    acct = AccountSummary(
        account="U9999999",
        net_liquidation=250_000.0,
        total_cash=30_000.0,
        buying_power=60_000.0,
        day_pnl=1_200.0,
        unrealized_pnl=15_000.0,
        realized_pnl=3_000.0,
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(acct)
    await db_session.commit()

    result = await db_session.execute(
        select(AccountSummary).where(AccountSummary.account == "U9999999")
    )
    fetched = result.scalar_one()

    assert fetched.net_liquidation == 250_000.0
    assert fetched.day_pnl == 1_200.0


# ---------------------------------------------------------------------------
# SyncLog
# ---------------------------------------------------------------------------

async def test_sync_log_crud(db_session):
    from sqlalchemy import select

    from backend.models.sync_log import SyncLog

    log = SyncLog(
        sync_type="positions",
        status="success",
        started_at=datetime.now(timezone.utc),
        records_updated=12,
    )
    db_session.add(log)
    await db_session.commit()

    result = await db_session.execute(
        select(SyncLog).where(SyncLog.sync_type == "positions")
    )
    fetched = result.scalar_one()

    assert fetched.status == "success"
    assert fetched.records_updated == 12


# ---------------------------------------------------------------------------
# ResearchCache
# ---------------------------------------------------------------------------

async def test_research_cache_crud(db_session):
    from sqlalchemy import select

    from backend.models.research_cache import ResearchCache

    now = datetime.now(timezone.utc)
    from datetime import timedelta
    expires = now + timedelta(hours=24)

    entry = ResearchCache(
        symbol="META",
        briefing_type="holding_brief",
        content="## META Analysis\nStrong ad revenue growth...",
        model="claude-opus-4-5",
        expires_at=expires,
    )
    db_session.add(entry)
    await db_session.commit()

    result = await db_session.execute(
        select(ResearchCache).where(ResearchCache.symbol == "META")
    )
    fetched = result.scalar_one()

    assert fetched.briefing_type == "holding_brief"
    assert fetched.model == "claude-opus-4-5"
    assert fetched.expires_at is not None


# ---------------------------------------------------------------------------
# UserPreferences
# ---------------------------------------------------------------------------

async def test_user_preferences_crud(db_session):
    from sqlalchemy import select

    from backend.models.user_preferences import UserPreferences

    prefs = UserPreferences(
        id=1,
        investment_horizon="long",
        risk_tolerance="moderate",
        max_single_position_pct=10.0,
        max_sector_pct=25.0,
        tax_sensitive=False,
        min_confidence_to_act=60,
        scale_in_enabled=True,
        scale_in_tranches=3,
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(prefs)
    await db_session.commit()

    result = await db_session.execute(select(UserPreferences).where(UserPreferences.id == 1))
    fetched = result.scalar_one()

    assert fetched.investment_horizon == "long"
    assert fetched.min_confidence_to_act == 60
    assert fetched.scale_in_tranches == 3


# ---------------------------------------------------------------------------
# Recommendation
# ---------------------------------------------------------------------------

async def test_recommendation_crud(db_session):
    from sqlalchemy import select

    from backend.models.recommendation import Recommendation

    from datetime import timedelta
    now = datetime.now(timezone.utc)

    rec = Recommendation(
        symbol="AMZN",
        action="ADD",
        urgency="medium",
        suggested_size_pct=3.0,
        suggested_tranche=2,
        total_tranches=3,
        timing_note="Wait for post-earnings pullback",
        rationale="Strong cloud growth; quality compounder at fair valuation.",
        conflicting_signals='["mean_reversion:SELL"]',
        supporting_strategies='["growth","quality"]',
        risk_factors='["macro slowdown"]',
        model_used="claude-sonnet-4-5",
        expires_at=now + timedelta(hours=24),
    )
    db_session.add(rec)
    await db_session.commit()

    result = await db_session.execute(
        select(Recommendation).where(Recommendation.symbol == "AMZN")
    )
    fetched = result.scalar_one()

    assert fetched.action == "ADD"
    assert fetched.urgency == "medium"
    assert fetched.suggested_tranche == 2


# ---------------------------------------------------------------------------
# Watchlist
# ---------------------------------------------------------------------------

async def test_watchlist_crud(db_session):
    from sqlalchemy import select

    from backend.models.watchlist import Watchlist

    item = Watchlist(
        symbol="TSM",
        notes="Semiconductor leader; wait for dip below 150",
        target_price=145.0,
        alert_enabled=True,
    )
    db_session.add(item)
    await db_session.commit()

    result = await db_session.execute(select(Watchlist).where(Watchlist.symbol == "TSM"))
    fetched = result.scalar_one()

    assert fetched.symbol == "TSM"
    assert fetched.target_price == 145.0
    assert fetched.alert_enabled is True
