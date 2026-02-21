# PortfolioIQ — Iteration 1 Task Breakdown (P0)

Each task is independently implementable and has a clear definition of done (DoD).
Work through tasks in order — later tasks depend on earlier ones.

**Pacing:**
- TASK-001 through TASK-005 (Layer 1 — Infrastructure): implement one at a time; verify before continuing
- TASK-006 through TASK-013 (Layer 2 — Data sync + API): implement as a group, verify at the end
- TASK-014 through TASK-018 (Layer 3 — Intelligence): implement as a group, verify at the end
- TASK-019 through TASK-027 (Layer 4 — Frontend): implement as a group, verify at the end

---

## Layer 1 — Infrastructure

### TASK-001: Create Directory Scaffold

Create all project directories and add `__init__.py` to Python packages.

**Directories:**
```
backend/
backend/models/
backend/services/
backend/routers/
backend/strategies/
backend/mcp/
tests/
frontend/src/
frontend/src/components/ui/
frontend/src/components/layout/
frontend/src/components/dashboard/
frontend/src/pages/
frontend/src/hooks/
frontend/src/lib/
frontend/src/stores/
```

**Python packages** (add empty `__init__.py`):
```
backend/__init__.py
backend/models/__init__.py
backend/services/__init__.py
backend/routers/__init__.py
backend/strategies/__init__.py
backend/mcp/__init__.py
tests/__init__.py
```

**Definition of done:** Running `python -c "import backend"` from project root succeeds.

---

### TASK-002: Install Dependencies

Install Python and Node dependencies.

**Steps:**
1. Run `uv sync` in project root — creates `.venv/` and installs all dependencies from `pyproject.toml`
2. Run `npm install` in `frontend/` — installs all deps from `package.json`

**Definition of done:**
- `.venv/` directory exists with all packages installed
- `uv run python -c "import fastapi, sqlalchemy, ib_insync, yfinance, anthropic"` succeeds
- `frontend/node_modules/` exists
- `npm run type-check` in `frontend/` exits without errors (on empty src)

---

### TASK-002b: Test Fixtures Setup

Create the shared pytest fixture file that all subsequent tests depend on.

**File to create:** `tests/conftest.py`

Fixtures:
- `async_engine` — in-memory SQLite engine (`sqlite+aiosqlite:///:memory:`) with `create_all` applied to `Base.metadata`
- `db_session` — async `AsyncSession` scoped to each test, with rollback on teardown
- `test_client` — FastAPI `AsyncClient` with `get_session` dependency overridden to use `db_session`
- `sample_position` — inserts a `Position` row for symbol `"TEST"` into the test DB and returns it
- `sample_fundamentals` — inserts a `Fundamentals` row for symbol `"TEST"` into the test DB and returns it
- `mock_yfinance_ticker` — `unittest.mock.patch` on `yfinance.Ticker` returning a `MagicMock` with canned `.history()` DataFrame and `.info` dict
- `mock_claude_response` — `AsyncMock` returning a valid `SmartRecommendation` JSON structure

**Definition of done:**
- `uv run pytest tests/ --collect-only` runs without errors and reports fixtures available
- `uv run pytest tests/test_models.py` passes (once TASK-003 is done)

---

### TASK-003: Database Models

Implement SQLAlchemy ORM models for all tables. One file per model.

**Files to create:**
- `backend/models/__init__.py` — imports all models for Alembic autodiscovery
- `backend/models/base.py` — `DeclarativeBase` and `TimestampMixin`
- `backend/models/position.py` — `Position` model
- `backend/models/transaction.py` — `Transaction` model
- `backend/models/market_data.py` — `MarketData`, `Fundamentals` models
- `backend/models/account.py` — `AccountSummary` model
- `backend/models/signal.py` — `Signal` model
- `backend/models/recommendation.py` — `Recommendation` model
- `backend/models/preferences.py` — `UserPreferences` model
- `backend/models/watchlist.py` — `WatchlistItem` model
- `backend/models/research.py` — `ResearchCache` model
- `backend/models/sync_log.py` — `SyncLog` model

Use SQLAlchemy 2.0 mapped_column syntax with type annotations.

**Definition of done:**
- `uv run python -c "from backend.models import *; print('OK')"` succeeds
- `tests/test_models.py`: import all models; create + query each in test DB using `db_session` fixture — all pass

---

### TASK-004: Alembic Setup + Initial Migration

Set up Alembic for database migrations and apply the initial migration.

**Steps:**
1. Run `uv run alembic init alembic` — creates `alembic/` directory and `alembic.ini`
2. Edit `alembic.ini`: set `sqlalchemy.url = sqlite:///./portfolioiq.db`
3. Edit `alembic/env.py`:
   - Import `settings` from `backend.config`
   - Import all models: `from backend.models import *`
   - Set `target_metadata = Base.metadata`
   - Override `get_url()` to use `settings.database_url`
4. Generate migration: `uv run alembic revision --autogenerate -m "initial"`
5. Apply migration: `uv run alembic upgrade head`

**Definition of done:**
- `portfolioiq.db` file exists
- Running `sqlite3 portfolioiq.db ".tables"` shows all expected tables

---

### TASK-005: FastAPI Application Skeleton + Config

Create the core application files: config, database session factory, and FastAPI app with health endpoint.

**Files to create:**

`backend/config.py`:
```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    ibkr_host: str = "127.0.0.1"
    ibkr_tws_port: int = 4002
    ibkr_client_id: int = 1
    ibkr_account: str = ""
    anthropic_api_key: str = ""
    database_url: str = "sqlite+aiosqlite:///./portfolioiq.db"
    app_env: str = "development"
    log_level: str = "INFO"
    sync_interval_minutes: int = 5
    quote_refresh_seconds: int = 60
    ohlcv_cache_ttl_hours: int = 24
    fundamental_cache_ttl_hours: int = 6
    research_cache_ttl_hours: int = 24
    research_daily_call_limit: int = 20
    research_model: str = "claude-opus-4-5"
    signal_model: str = "claude-sonnet-4-5"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
```

`backend/database.py`:
- Async engine with `create_async_engine`
- `AsyncSession` factory
- `get_session()` dependency for FastAPI

`backend/main.py`:
- FastAPI app with title "PortfolioIQ"
- CORS middleware allowing `http://localhost:5173`
- `GET /api/health` endpoint returning `{ "status": "ok", "version": "0.1.0" }`
- Lifespan context manager (placeholder for scheduler startup in TASK-010)

**Definition of done:**
- `uv run uvicorn backend.main:app --reload --port 8000` starts without errors
- `curl http://localhost:8000/api/health` returns `{"status":"ok","version":"0.1.0"}`
- `tests/routers/test_health.py`: `GET /api/health` via `test_client` returns 200 + expected JSON — passes

---

## Layer 2 — Data Sync + API

### TASK-006: IBKR Connection Manager

`backend/services/ibkr_client.py`

- `IBKRClient` class wrapping `ib_insync.IB`
- `connect()` / `disconnect()` with retry logic (tenacity)
- `is_connected()` property
- `get_ib()` — returns the connected IB instance (raises if not connected)
- Reconnect callback on disconnect event

**Definition of done:** With TWS running on port 4002:
```python
uv run python -c "
import asyncio
from backend.services.ibkr_client import IBKRClient
from backend.config import settings
async def test():
    client = IBKRClient(settings)
    await client.connect()
    print('connected:', client.is_connected())
    await client.disconnect()
asyncio.run(test())
"
```
Prints `connected: True`.

---

### TASK-007: Position Sync Service

`backend/services/ibkr_sync.py` — `sync_positions()` function

- Fetch `ib.portfolio()` filtered to `secType == 'STK'`
- For each item: map to `Position` fields, upsert using SQLAlchemy `merge()` or raw `INSERT OR REPLACE`
- Enrich with sector/industry from `fundamentals` table if already cached (don't block on it)
- Log results to `sync_log` table

**Definition of done:** After calling `sync_positions()`, the `positions` table contains all current IBKR stock holdings.

---

### TASK-008: Transaction Sync Service

In `backend/services/ibkr_sync.py` — `sync_transactions()` function

- Fetch fills from last 90 days via `ib.reqFillsAsync()`
- Map to `Transaction` model; use `ibkr_trade_id` (execution ID) for deduplication
- Upsert with `INSERT OR IGNORE` on `ibkr_trade_id` UNIQUE constraint
- Log results to `sync_log`

**Definition of done:** After calling `sync_transactions()`, the `transactions` table is populated and re-running does not create duplicates.

---

### TASK-009: Account Balance Sync

In `backend/services/ibkr_sync.py` — `sync_account_summary()` function

- Fetch `ib.accountSummary()` for the configured account
- Extract: `NetLiquidation`, `TotalCashValue`, `BuyingPower`, `DayNPnL`, `UnrealizedPnL`, `RealizedPnL`
- Upsert single row in `account_summary` table

**Definition of done:** `account_summary` table has a row with correct values after calling the function.

---

### TASK-010: APScheduler Setup

`backend/scheduler.py`

- `AsyncIOScheduler` from APScheduler
- Jobs:
  - `sync_all`: every `SYNC_INTERVAL_MINUTES` minutes — runs position, transaction, balance sync
  - `refresh_quotes`: every `QUOTE_REFRESH_SECONDS` seconds — updates current prices for all positions
- Integrate into `backend/main.py` lifespan: start scheduler on startup, stop on shutdown

**Definition of done:**
- Backend starts and log shows sync job scheduled
- After 5 minutes, positions table shows updated `last_updated` timestamp

---

### TASK-011: yfinance Market Data Service

`backend/services/market_data.py`

Three public functions:

`get_quote(symbol, db) -> dict`:
- Check `market_data` table for entry within TTL (60s market hours, 15min after hours)
- If fresh: return cached data
- If stale: fetch `yf.Ticker(symbol).fast_info`, update `market_data`, return

`get_history(symbol, period, db) -> list[dict]`:
- Check `market_data` table for full OHLCV series within TTL (24h)
- If stale: fetch `yf.Ticker(symbol).history(period=period)`, upsert all rows, return

`get_fundamentals(symbol, db) -> dict`:
- Check `fundamentals` table for entry within TTL (6h)
- If stale: fetch `yf.Ticker(symbol).info`, map to `Fundamentals` model, upsert, return

**Definition of done:**
- First call fetches from yfinance (takes ~1-2s)
- Second call within TTL returns immediately from cache
- `tests/services/test_market_data.py`: cache hit returns DB row; cache miss calls `mock_yfinance_ticker`; TTL expiry triggers re-fetch — all pass

---

### TASK-012: Portfolio API Router

`backend/routers/portfolio.py`

Endpoints:
- `GET /api/portfolio/summary` — net_liquidation, day_pnl, unrealized_pnl, cash, buying_power, last_sync
- `GET /api/portfolio/positions` — all positions with current prices joined from market_data cache
- `GET /api/portfolio/position/{symbol}` — single position + last 20 transactions for that symbol
- `GET /api/portfolio/transactions` — paginated; query params: `page`, `limit`, `symbol`
- `POST /api/portfolio/sync` — trigger `sync_all()` immediately, return sync result

Include Pydantic response schemas in the router file.

**Definition of done:**
- `GET /api/portfolio/positions` returns a non-empty JSON array matching the positions in IBKR
- `tests/routers/test_portfolio.py`: `GET /api/portfolio/positions` with `sample_position` seeded in test DB returns correct JSON — passes

---

### TASK-013: Market Data API Router

`backend/routers/market.py`

Endpoints:
- `GET /api/market/quote/{symbol}` — current price, change, change_pct, volume
- `GET /api/market/history/{symbol}` — OHLCV; query params: `period` (default "1y"), `interval` (default "1d")
- `GET /api/market/fundamentals/{symbol}` — all fundamental fields

**Definition of done:**
- `GET /api/market/quote/AAPL` returns current AAPL price
- `tests/routers/test_market.py`: `GET /api/market/quote/{sym}` with `mock_yfinance_ticker` returns correct quote JSON — passes

---

## Layer 3 — Intelligence

### TASK-014: Strategy Engine Base

`backend/strategies/base.py`

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

@dataclass
class StrategySignal:
    symbol: str
    strategy: str
    signal: Literal["BUY", "SELL", "HOLD"]
    confidence: int
    reasoning: str
    key_metrics: dict
    created_at: datetime = field(default_factory=datetime.utcnow)

class BaseStrategy(ABC):
    strategy_id: str
    strategy_name: str

    @abstractmethod
    async def compute(
        self,
        symbol: str,
        ohlcv: pd.DataFrame,
        fundamentals: dict,
        position: dict | None,
        preferences: dict,
    ) -> StrategySignal:
        ...
```

**Definition of done:** `from backend.strategies.base import BaseStrategy, StrategySignal` imports cleanly.

---

### TASK-015: Momentum Strategy

`backend/strategies/momentum.py` — `MomentumStrategy(BaseStrategy)`

Implement full momentum logic from `docs/STRATEGIES.md`:
- Use `pandas_ta` for RSI, MACD, SMA(200)
- Compute 52-week high/low proximity
- Compute 90-day return and 10d/90d volume ratio
- Apply BUY/SELL/HOLD rules and confidence scoring

**Definition of done:**
- `tests/strategies/test_momentum.py`: BUY signal with uptrend OHLCV data; SELL with overbought RSI; HOLD for neutral conditions — all pass

---

### TASK-016: Value Strategy

`backend/strategies/value.py` — `ValueStrategy(BaseStrategy)`

Implement value logic from `docs/STRATEGIES.md`:
- Read P/E, FCF yield, EV/EBITDA from fundamentals dict
- Read sector median P/E and EV/EBITDA from fundamentals dict (populated by market data service)
- Apply BUY/SELL/HOLD rules and confidence scoring

**Definition of done:**
- `tests/strategies/test_value.py`: BUY when P/E < 0.75× median + FCF yield > 5%; SELL when P/E > 2× median — all pass

---

### TASK-016b: Growth Strategy

`backend/strategies/growth.py` — `GrowthStrategy(BaseStrategy)`

Implement growth logic from `docs/STRATEGIES.md`:
- Revenue CAGR, EPS CAGR, gross margin, PEG ratio from fundamentals
- BUY/SELL/HOLD rules and confidence scoring

**Definition of done:**
- `tests/strategies/test_growth.py`: BUY on high CAGR + low PEG; SELL on margin compression — all pass

---

### TASK-016c: Long-Term Compounder Strategy

`backend/strategies/long_term.py` — `LongTermStrategy(BaseStrategy)`

Implement long-term logic from `docs/STRATEGIES.md`:
- Default signal is HOLD for existing positions
- BUY only on quality + valuation meeting thresholds
- SELL requires sustained fundamental deterioration (uses historical fundamentals if available, otherwise conservative)

**Definition of done:**
- `tests/strategies/test_long_term.py`: HOLD for solid company fundamentals; SELL for sustained fundamental deterioration — all pass

---

### TASK-016d: Hybrid Strategy Profile Engine

`backend/strategies/hybrid.py` — `HybridStrategy(BaseStrategy)`

- Takes a `HybridProfile` config (list of `StrategyWeight` + `holding_bias`)
- Computes each component strategy's signal
- Blends confidence using weighted average
- Applies `holding_bias` logic (suppress technical SELL signals if bias = `long`)

Preset profiles defined in `backend/strategies/hybrid.py` as constants.

**Definition of done:**
- `tests/strategies/test_hybrid.py`: Growth+LT profile with `holding_bias="long"` suppresses Momentum SELL and returns HOLD — passes

---

### TASK-017: Signal Generation Service

`backend/services/strategy_engine.py`

`generate_all_signals(db, settings) -> list[StrategySignal]`:
- Reads all positions from DB
- For each position:
  - Fetches OHLCV (from cache or yfinance)
  - Fetches fundamentals (from cache or yfinance)
  - Runs all enabled strategies (from user preferences)
  - Runs all configured hybrid profiles
- Writes results to `signals` table (replace existing for same symbol+strategy)

**Definition of done:** `POST /api/signals/refresh` populates the signals table with BUY/SELL/HOLD for each position × strategy.

---

### TASK-017b: User Preferences Service + API

`backend/routers/preferences.py`

- `GET /api/preferences` — returns current preferences (creates default row if none exists)
- `PUT /api/preferences` — update preferences; body is partial update

Seed default preferences on first-run (in FastAPI lifespan or first GET).

**Definition of done:** `GET /api/preferences` returns valid JSON with all preference fields.

---

### TASK-017c: Smart Recommendation Engine

`backend/services/recommendation_engine.py`

`generate_all_recommendations(db, settings) -> list[SmartRecommendation]`:
- Reads all positions (and watchlist items)
- For each symbol:
  - Reads strategy signals from DB
  - Reads portfolio context (position weight, sector weight, available cash)
  - Reads user preferences
  - Builds prompt using template from `docs/STRATEGIES.md`
  - Calls Claude API (`claude-sonnet-4-5`)
  - Parses JSON response into `SmartRecommendation`
  - Writes to `recommendations` table

Rate limit check: enforce `RESEARCH_DAILY_CALL_LIMIT` across research + recommendation calls.

**Definition of done:**
- `POST /api/recommendations/refresh` runs and populates the recommendations table with AI-generated actions and rationale
- `tests/services/test_recommendation_engine.py`: `mock_claude_response` returns valid JSON; Pydantic validation passes; daily limit check enforced — all pass

---

### TASK-018: Signals + Recommendations API Routers

`backend/routers/signals.py`:
- `GET /api/signals` — all current signals, query param: `symbol` or `strategy` filter
- `GET /api/signals/{symbol}` — signals for one symbol
- `POST /api/signals/refresh` — trigger strategy engine

`backend/routers/recommendations.py`:
- `GET /api/recommendations` — all current recommendations
- `GET /api/recommendations/{symbol}` — recommendation for one symbol
- `POST /api/recommendations/refresh` — trigger recommendation engine

**Definition of done:**
- `GET /api/recommendations` returns an array with at least one item containing `action`, `urgency`, `rationale`, `suggested_size_pct`
- `tests/routers/test_signals.py`: `GET /api/signals` returns seeded signals; `POST /api/signals/refresh` triggers engine — passes
- `tests/routers/test_recommendations.py`: `GET /api/recommendations` returns seeded recommendations — passes

---

## Layer 4 — Frontend

### TASK-019: Frontend Vite Scaffold + Tailwind + shadcn/ui

1. Run `npm install` in `frontend/` (already have package.json)
2. Initialize shadcn/ui: `npx shadcn@latest init` — accept defaults, dark theme
3. Create `frontend/src/index.css` with Tailwind v4 import and dark theme CSS variables
4. Create minimal `frontend/src/main.tsx` (ReactDOM.createRoot)
5. Create minimal `frontend/src/App.tsx` (returns `<div>PortfolioIQ</div>`)

**Definition of done:** `npm run dev` starts at port 5173; browser shows dark background with "PortfolioIQ" text.

---

### TASK-020: API Client + React Query Setup

`frontend/src/lib/api.ts`:
- Base `apiFetch()` function wrapping `fetch` with base URL `/api`
- Typed functions: `getPortfolioSummary()`, `getPositions()`, `getSignals()`, `getRecommendations()`, `getPreferences()`

`frontend/src/main.tsx`:
- Wrap app in `QueryClientProvider` with `QueryClient`

`frontend/src/hooks/`:
- `usePortfolioSummary.ts` — `useQuery({ queryKey: ['summary'], queryFn: api.getPortfolioSummary })`
- `usePositions.ts`
- `useSignals.ts`
- `useRecommendations.ts`

**Definition of done:** In React DevTools → TanStack Query tab, all queries show data from the backend.

---

### TASK-021: App Shell + Routing

`frontend/src/App.tsx`:
- `BrowserRouter` + `Routes`
- Route: `/` → `<Dashboard />`
- Route: `/portfolio` → `<Portfolio />`
- Route: `/signals` → `<Signals />`
- Route: `/recommendations` → `<Recommendations />`
- Route: `/settings` → `<Settings />`

`frontend/src/components/layout/AppShell.tsx`:
- Fixed sidebar with navigation links
- Top header with connection status badge + last sync time
- Main content area

**Definition of done:** Navigating between sidebar links loads the correct page component.

---

### TASK-022: Portfolio Summary Cards

`frontend/src/components/dashboard/SummaryCards.tsx`:
- 4 cards: Total Portfolio Value, Day P&L ($+%), Total Unrealized P&L ($+%), Cash
- Color-coded P&L: positive = green text/border, negative = red
- Skeleton loading state while data fetches

**Definition of done:** Dashboard shows 4 cards with real data from `/api/portfolio/summary`.

---

### TASK-023: Positions Table

`frontend/src/components/portfolio/PositionsTable.tsx`:
- Columns: Symbol, Shares, Avg Cost, Current Price, Market Value, Unrealized P&L ($), Unrealized P&L (%)
- Sortable by any column (ascending/descending toggle)
- P&L values color-coded (green/red)
- Monospace font for numbers
- Loading skeleton for each row

**Definition of done:** Table renders all IBKR positions with correct values.

---

### TASK-024: Sector Allocation Chart

`frontend/src/components/dashboard/SectorChart.tsx`:
- Recharts `PieChart` (donut style, innerRadius=60)
- Each slice = one sector; color from a curated palette
- Custom tooltip: sector name, % of portfolio, $ value
- Legend below chart

**Definition of done:** Chart shows correct sector breakdown matching positions data.

---

### TASK-025: Raw Signals View

`frontend/src/pages/Signals.tsx`:
- Toggle: "By Symbol" | "By Strategy" view
- Table/grid showing: Symbol, Strategy, Signal badge, Confidence bar, Key metrics chips
- BUY = green badge, SELL = red badge, HOLD = gray badge
- "Refresh Signals" button calls `POST /api/signals/refresh` via `useMutation`

**Definition of done:** Signals page shows live strategy signals for all holdings.

---

### TASK-026: Smart Recommendations View

`frontend/src/pages/Recommendations.tsx`:
- Card grid layout, one card per symbol
- Card shows: Symbol, Action badge (color-coded), Urgency chip, Suggested size %
- Tranche indicator: "Tranche 1 of 3" pill
- Timing note (if present)
- Expandable section: full rationale, conflicting signals, risk factors
- "Refresh" button calls `POST /api/recommendations/refresh`

**Definition of done:** Recommendations page shows AI-generated guidance with expandable rationale.

---

### TASK-027: Preferences / Settings Page

`frontend/src/pages/Settings.tsx`:
- Investment horizon: 3-option selector (Short / Medium / Long)
- Risk tolerance: 3-option selector (Conservative / Moderate / Aggressive)
- Max single position %: slider (1–20%)
- Max sector %: slider (10–40%)
- Strategy toggles: checkbox per strategy (momentum, value, growth, long_term, quality, dividend_growth, mean_reversion)
- Hybrid profile builder: add/edit/remove custom blends with weight sliders + holding bias selector
- Tax sensitive: toggle
- Min confidence to act: slider (0–100)
- Scale-in: toggle + tranche count stepper
- Save button: calls `PUT /api/preferences` then triggers recommendation refresh

**Definition of done:** Changing preferences and saving produces updated recommendations on the Recommendations page.
