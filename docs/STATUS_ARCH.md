# PortfolioIQ — Architecture & Implementation Status
**Audience:** Architect / Developer
**Last updated:** February 2026
**Branch:** `feat/task-003-models` (ready for PR → `main`)

---

## System Architecture in One Paragraph

PortfolioIQ is a local-only, single-user app. A FastAPI backend (port 8000) serves a React SPA (port 5173, Vite dev server). All persistence is SQLite via SQLAlchemy async. IBKR portfolio data is synced on a 5-minute APScheduler loop using `ib_insync`. Market data and fundamentals are fetched from yfinance and cached in SQLite. Seven rule-based strategy engines emit `StrategySignal` objects; those signals — plus portfolio context and user preferences — are fed to `claude-sonnet-4-5` to produce a `SmartRecommendation` per position. Three optional MCP servers (stdio transport) expose portfolio, market, and research tools to Claude Desktop or agent workflows.

---

## Repository Layout (Current State)

```
PortfolioIQ/
├── pyproject.toml              # uv-managed Python deps + ruff/mypy/pytest config
├── .env.example                # all env var keys with defaults
├── backend/
│   ├── __init__.py
│   ├── models/                 # ✅ COMPLETE — 12 SQLAlchemy ORM models
│   │   ├── base.py             # DeclarativeBase
│   │   ├── position.py
│   │   ├── transaction.py
│   │   ├── market_data.py
│   │   ├── fundamentals.py
│   │   ├── signal.py
│   │   ├── account_summary.py
│   │   ├── sync_log.py
│   │   ├── research_cache.py
│   │   ├── user_preferences.py
│   │   ├── recommendation.py
│   │   ├── watchlist.py
│   │   └── __init__.py         # re-exports all 12 for Alembic autodiscovery
│   ├── services/               # ⬜ not yet implemented
│   ├── routers/                # ⬜ not yet implemented
│   ├── strategies/             # ⬜ not yet implemented
│   └── mcp/                    # ⬜ not yet implemented
├── tests/
│   ├── conftest.py             # ✅ COMPLETE — shared async fixtures
│   └── test_models.py          # ✅ COMPLETE — 12/12 CRUD tests pass
├── docs/
│   ├── ARCHITECTURE.md         # full system design + DB schema + API + MCP design
│   ├── TASKS.md                # Iteration 1 task breakdown (TASK-001 to TASK-027)
│   ├── STRATEGIES.md           # all 7 strategy definitions + confidence formulas
│   ├── PRODUCT.md              # feature spec P0/P1/P2
│   └── INTEGRATIONS.md         # IBKR, yfinance, Claude API, MCP setup guide
└── frontend/                   # React app (scaffolded, not yet implemented)
    ├── package.json
    ├── vite.config.ts          # @tailwindcss/vite plugin + /api proxy to :8000
    └── src/                    # empty .gitkeep placeholders
```

---

## Task Completion Status

### Layer 1 — Infrastructure (TASK-001 to TASK-005)

| Task | Status | Artifact |
|------|--------|---------|
| TASK-001: Directory scaffold + `__init__.py` files | ✅ Done | All dirs exist; `import backend` succeeds |
| TASK-002: `uv sync` + `npm install` | ✅ Done | `.venv/` and `frontend/node_modules/` present |
| TASK-002b: `tests/conftest.py` fixtures | ✅ Done | 7 fixtures; all usable without FastAPI or IBKR |
| TASK-003: SQLAlchemy ORM models | ✅ Done | 12 models; 12/12 CRUD tests pass |
| TASK-004: Alembic init + initial migration | ⬜ Next | No `alembic/` dir yet |
| TASK-005: `config.py`, `database.py`, `main.py` | ⬜ Pending | No application files yet |

### Layer 2 — Data Sync + API (TASK-006 to TASK-013)
All pending. Depends on TASK-004 and TASK-005.

### Layer 3 — Intelligence (TASK-014 to TASK-018)
All pending. Depends on Layer 2.

### Layer 4 — Frontend (TASK-019 to TASK-027)
All pending. Depends on Layer 3.

---

## Database Schema — Implemented Models

All models extend `Base` from `backend/models/base.py` (`DeclarativeBase`). Column types use SQLAlchemy 2.x `Mapped[T]` / `mapped_column()` syntax throughout.

### `positions` — IBKR portfolio positions
```
id, symbol, account, shares, avg_cost, current_price, market_value,
unrealized_pnl, unrealized_pnl_pct, realized_pnl, sector, industry,
last_updated
UNIQUE(symbol, account)
```

### `transactions` — Executed trades and corporate actions
```
id, symbol, account, trade_date, settle_date, action (BUY/SELL/DIV...),
shares, price, commission, amount, description, ibkr_trade_id (UNIQUE),
created_at
```

### `market_data` — Daily OHLCV cache (yfinance)
```
id, symbol, date, open, high, low, close, volume, adj_close, created_at
UNIQUE(symbol, date)
```

### `fundamentals` — Per-symbol fundamental cache (yfinance)
```
id, symbol (UNIQUE), pe_ratio, pb_ratio, ev_ebitda, fcf_yield, roe, roic,
debt_equity, gross_margin, dividend_yield, payout_ratio, eps_growth_5y,
dividend_cagr_5y, consecutive_div_growth_years, sector, industry, updated_at
```

### `signals` — Raw strategy signal output
```
id, symbol, strategy, signal (BUY/SELL/HOLD), confidence (0-100 CHECK),
reasoning, key_metrics (JSON text), created_at, expires_at
```

### `recommendations` — AI-synthesised SmartRecommendation
```
id, symbol, action (BUY/ADD/TRIM/SELL/HOLD/WATCH), urgency (high/medium/low),
suggested_size_pct, suggested_tranche, total_tranches, timing_note,
rationale, conflicting_signals (JSON), supporting_strategies (JSON),
risk_factors (JSON), model_used, created_at, expires_at
```

### `account_summary` — IBKR account balances
```
id, account (UNIQUE), net_liquidation, total_cash, buying_power,
day_pnl, unrealized_pnl, realized_pnl, updated_at
```

### `sync_log` — Audit trail for sync jobs
```
id, sync_type (positions/transactions/balances/market_data),
status (success/failed/partial), started_at, completed_at,
records_updated, error_message
```

### `research_cache` — Claude briefings per symbol
```
id, symbol, briefing_type (holding_brief/watchlist_analysis),
content, model, created_at, expires_at
UNIQUE(symbol, briefing_type)
```

### `user_preferences` — Single-row config table (id=1)
```
id=1, investment_horizon, risk_tolerance, max_single_position_pct,
max_sector_pct, preferred_strategies (JSON), hybrid_profiles (JSON),
tax_sensitive, min_confidence_to_act, scale_in_enabled, scale_in_tranches,
updated_at
```

### `watchlist`
```
id, symbol (UNIQUE), added_at, notes, target_price, alert_enabled
```

---

## Tech Stack — Key Decisions and Rationale

| Decision | Choice | Why |
|----------|--------|-----|
| Python package manager | `uv` | Faster than pip/poetry; lockfile-based reproducibility |
| ORM | SQLAlchemy 2.x async (`AsyncSession`, `Mapped[]`) | Fully typed, async-native; pairs well with FastAPI's async model |
| DB driver | `aiosqlite` | Zero-config local SQLite; avoids network DB dependency for a local-only app |
| TA library | `pandas-ta` | Pure Python — avoids `ta-lib`'s C compilation requirement (Windows pain) |
| IBKR integration | `ib_insync` (TWS API) | Avoids Client Portal API's browser-auth flow; works headless |
| AI model (recommendations) | `claude-sonnet-4-5` | Best reasoning-to-cost ratio for structured signal synthesis |
| AI model (research) | `claude-opus-4-5` | Web search + deep analysis; used sparingly (daily call limit enforced) |
| Frontend state — server | TanStack Query | Standard for React async data; avoids `useEffect`+fetch anti-pattern |
| Frontend state — client | Zustand | Minimal boilerplate for UI-only state (sidebar, modal open state) |
| CSS framework | Tailwind v4 | Uses `@tailwindcss/vite` plugin — **no `tailwind.config.js`** (v4 changed this) |
| Component library | shadcn/ui | Unstyled Radix primitives + Tailwind; fully ownable, no vendor lock-in |
| Scheduling | APScheduler | In-process job scheduler; integrates with FastAPI lifespan |

---

## Test Infrastructure

### Fixtures (`tests/conftest.py`)

| Fixture | Scope | What It Does |
|---------|-------|-------------|
| `async_engine` | function | `create_async_engine("sqlite+aiosqlite:///:memory:")` + `Base.metadata.create_all` |
| `db_session` | function | `AsyncSession` yielded from in-memory engine; rolls back on teardown |
| `test_client` | function | FastAPI `AsyncClient` (httpx) with `get_session` dependency overridden to `db_session` |
| `sample_position` | function | Inserts `Position(symbol="TEST", ...)` into `db_session`; returns ORM instance |
| `sample_fundamentals` | function | Inserts `Fundamentals(symbol="TEST", ...)` into `db_session`; returns ORM instance |
| `mock_yfinance_ticker` | function | `patch("yfinance.Ticker")` → `MagicMock` with 252-day OHLCV `DataFrame` + `info` dict |
| `mock_claude_response` | function | `AsyncMock` on `anthropic.AsyncAnthropic.messages.create` returning valid SmartRecommendation JSON |

**Key constraint:** `test_client` imports `backend.database` and `backend.main` *inside* the fixture body (not at module level) so that pytest collection and non-`test_client` tests work before TASK-005 (FastAPI app) is implemented.

### Running Tests
```bash
uv run pytest                          # all tests
uv run pytest tests/test_models.py -v  # models only (no FastAPI needed)
uv run pytest --co -q                  # collect-only — verify no import errors
uv run pytest tests/strategies/        # strategies only (once Layer 3 is built)
```

### Config
```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"   # no @pytest.mark.asyncio decorator needed
testpaths = ["tests"]
```

### Mocking Conventions
- All external I/O mocked at the service boundary — no real network calls in tests
- yfinance: `patch("yfinance.Ticker")`
- Claude API: `patch("anthropic.AsyncAnthropic.messages.create")`
- IBKR: `AsyncMock` of `IBKRClient`

---

## What TASK-004 Needs to Do (Next)

1. `alembic init alembic` — creates `alembic/` directory + `alembic.ini`
2. Patch `alembic/env.py`:
   - Import `Base` from `backend.models`
   - Import `DATABASE_URL` from `backend.config` (Settings)
   - Set `target_metadata = Base.metadata`
   - Use async engine pattern (`run_async_context`)
3. `alembic revision --autogenerate -m "initial"` — generates migration from models
4. `alembic upgrade head` — applies migration; `portfolioiq.db` created with all 12 tables
5. DoD: `sqlite3 portfolioiq.db ".tables"` lists all 12 table names

---

## What TASK-005 Needs to Do (After That)

Three files:

**`backend/config.py`** — `pydantic-settings` `Settings` class reading from `.env`:
```python
class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./portfolioiq.db"
    ibkr_host: str = "127.0.0.1"
    ibkr_tws_port: int = 4002
    anthropic_api_key: str = ""
    # ... etc.
```

**`backend/database.py`** — async engine + session factory + FastAPI dependency:
```python
engine = create_async_engine(settings.database_url)
async_session = async_sessionmaker(engine, expire_on_commit=False)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
```

**`backend/main.py`** — FastAPI app with CORS, lifespan, and `/api/health`:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # start APScheduler
    yield
    # stop APScheduler

app = FastAPI(lifespan=lifespan)

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
```

DoD: `uv run uvicorn backend.main:app --reload --port 8000` starts; `GET /api/health` returns 200.

---

## Validation Checkpoints

| After | Verify With |
|-------|------------|
| TASK-003 (now) | `uv run pytest tests/test_models.py -v` → 12 passed |
| TASK-004 | `sqlite3 portfolioiq.db ".tables"` → 12 table names |
| TASK-005 | `curl http://localhost:8000/api/health` → `{"status":"ok"}` |
| TASK-013 | `http://localhost:8000/docs` → Swagger UI with real IBKR data |
| TASK-018 | `GET /api/recommendations` → AI-generated SmartRecommendations |
| TASK-024 | Browser at `localhost:5173` → dashboard with live portfolio |

---

## Code Conventions

- **All async:** `async def` for every route and service method
- **No `os.environ` direct access:** all config via `backend/config.py` `Settings` instance
- **Format:** `ruff format backend/ --line-length 100`
- **Lint:** `ruff check backend/` (rules: E, F, I, UP, B, SIM)
- **Type check:** `mypy backend/` (strict mode)
- **Commits:** conventional commits — `feat:`, `fix:`, `chore:`, `refactor:`, `docs:`
- **One model per file** in `backend/models/`; one router per resource in `backend/routers/`
- **TDD:** test file committed in same commit as implementation
