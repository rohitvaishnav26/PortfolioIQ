# PortfolioIQ — Architecture

## System Overview

PortfolioIQ is a fully local application. There is no cloud backend or external database. All data — portfolio positions, market data cache, strategy signals, AI recommendations — lives in a SQLite file on the user's machine.

The system has three tiers:
1. **Data ingestion**: IBKR via `ib_insync` (TWS API) for portfolio data; yfinance for market data and fundamentals
2. **Intelligence**: Strategy engine (rule-based signals) → Recommendation Engine (Claude API synthesis)
3. **Presentation**: FastAPI REST backend → React SPA

---

## Component Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                            User Browser                               │
│   React + Vite (localhost:5173)                                       │
│   Dashboard │ Portfolio │ Signals │ Recommendations │ Settings        │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ HTTP / REST
┌──────────────────────────────▼───────────────────────────────────────┐
│                   FastAPI Backend (localhost:8000)                     │
│                                                                        │
│  ┌───────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ Portfolio │ │  Market  │ │ Signals  │ │  Recoms  │ │  Prefs   │  │
│  │  Router   │ │  Router  │ │  Router  │ │  Router  │ │  Router  │  │
│  └───────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │                         Services Layer                            │ │
│  │                                                                   │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────────┐ │ │
│  │  │  IBKRSync   │  │ MarketData  │  │     StrategyEngine       │ │ │
│  │  │  Service    │  │  Service    │  │  (momentum, value,       │ │ │
│  │  │             │  │  (yfinance  │  │   growth, long_term,     │ │ │
│  │  │  positions  │  │  + SQLite   │  │   quality, dividend,     │ │ │
│  │  │  txns       │  │  cache)     │  │   mean_reversion,        │ │ │
│  │  │  balances   │  │             │  │   hybrid profiles)       │ │ │
│  │  └─────────────┘  └─────────────┘  └────────────┬─────────────┘ │ │
│  │                                                   │               │ │
│  │                   ┌───────────────────────────────▼─────────────┐ │ │
│  │                   │         RecommendationEngine                 │ │ │
│  │                   │  • Reads all strategy signals                │ │ │
│  │                   │  • Reads portfolio context + user prefs      │ │ │
│  │                   │  • Calls Claude API (claude-sonnet-4-5)      │ │ │
│  │                   │  • Writes SmartRecommendation to DB          │ │ │
│  │                   │    action: BUY/ADD/TRIM/SELL/HOLD/WATCH      │ │ │
│  │                   │    scale-in tranches, timing notes, rationale│ │ │
│  │                   └─────────────────────────────────────────────┘ │ │
│  │                                                                   │ │
│  │  ┌──────────────────────────────────────────────────────────────┐ │ │
│  │  │                    ResearchAgent                              │ │ │
│  │  │  (claude-opus-4-5 + web search → per-holding briefings)      │ │ │
│  │  └──────────────────────────────────────────────────────────────┘ │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │                  SQLite DB  (portfolioiq.db)                      │ │
│  │  positions │ transactions │ market_data │ fundamentals            │ │
│  │  signals │ recommendations │ user_preferences                     │ │
│  │  account_summary │ watchlist │ sync_log │ research_cache          │ │
│  └──────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │
           ┌───────────────────────┼───────────────────────┐
           │ ib_insync (TWS API)   │ yfinance (HTTP)        │ Claude API
  ┌────────▼────────┐    ┌─────────▼────────┐    ┌─────────▼──────────┐
  │  IBKR TWS/GW    │    │  Yahoo Finance   │    │  Anthropic API     │
  │  (port 4002)    │    │  (public REST)   │    │  (Recommendations  │
  └─────────────────┘    └──────────────────┘    │   + Research)      │
                                                  └────────────────────┘

MCP Servers (separate processes, stdio transport — for agent/Claude Desktop use):
  portfolioiq-portfolio  → reads SQLite (positions, recommendations)
  portfolioiq-market     → queries yfinance
  portfolioiq-research   → calls Claude API with web search
```

---

## Data Flow

### 1. IBKR Sync (every 5 minutes via APScheduler)
```
APScheduler trigger
  → IBKRSyncService.sync_all()
    → ib_insync: ib.portfolio()        → upsert positions table
    → ib_insync: ib.executions()       → upsert transactions table
    → ib_insync: ib.accountSummary()   → upsert account_summary table
    → log result to sync_log table
```

### 2. Market Data (on-demand with TTL caching)
```
API request for quote/history/fundamentals
  → MarketDataService checks SQLite cache
    → cache hit (within TTL) → return cached data
    → cache miss → yfinance fetch → store in SQLite → return data

TTLs:
  quotes:       60s during market hours, 15min after hours
  OHLCV:        24 hours
  fundamentals: 6 hours
```

### 3. Signal Generation (on demand or post-sync)
```
POST /api/signals/refresh
  → StrategyEngine.generate_all_signals()
    → for each position:
      → run enabled strategies (momentum, value, growth, long_term, etc.)
      → run configured hybrid profiles
      → write StrategySignal records to signals table
```

### 4. Smart Recommendations (on demand)
```
POST /api/recommendations/refresh
  → RecommendationEngine.generate_all()
    → for each position:
      → read all strategy signals from DB
      → read portfolio context (current weight, available cash, sector %)
      → read user_preferences
      → read market conditions (VIX proxy, broad market trend)
      → call Claude API with structured prompt
      → parse response into SmartRecommendation
      → write to recommendations table
```

### 5. Research Briefings (on demand, 24h cache)
```
GET /api/research/{symbol}
  → check research_cache table (24h TTL)
    → cache hit → return cached briefing
    → cache miss:
      → ResearchAgent calls Claude API (claude-opus-4-5 + web search)
      → store result in research_cache
      → return briefing
```

---

## Database Schema

```sql
-- ============================================================
-- Portfolio Data
-- ============================================================

CREATE TABLE positions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol              TEXT NOT NULL,
    account             TEXT NOT NULL,
    shares              REAL NOT NULL,
    avg_cost            REAL NOT NULL,         -- cost basis per share
    current_price       REAL,
    market_value        REAL,
    unrealized_pnl      REAL,
    unrealized_pnl_pct  REAL,
    realized_pnl        REAL DEFAULT 0,
    sector              TEXT,
    industry            TEXT,
    last_updated        TIMESTAMP NOT NULL,
    UNIQUE(symbol, account)
);

CREATE TABLE transactions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol          TEXT NOT NULL,
    account         TEXT NOT NULL,
    trade_date      DATE NOT NULL,
    settle_date     DATE,
    action          TEXT NOT NULL,  -- BUY, SELL, DIV, SPLIT, etc.
    shares          REAL,
    price           REAL,
    commission      REAL DEFAULT 0,
    amount          REAL NOT NULL,  -- net cash impact
    description     TEXT,
    ibkr_trade_id   TEXT UNIQUE,    -- IBKR execution ID for deduplication
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE account_summary (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    account          TEXT UNIQUE NOT NULL,
    net_liquidation  REAL,
    total_cash       REAL,
    buying_power     REAL,
    day_pnl          REAL,
    unrealized_pnl   REAL,
    realized_pnl     REAL,
    updated_at       TIMESTAMP NOT NULL
);

-- ============================================================
-- Market Data Cache
-- ============================================================

CREATE TABLE market_data (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol      TEXT NOT NULL,
    date        DATE NOT NULL,
    open        REAL,
    high        REAL,
    low         REAL,
    close       REAL,
    volume      INTEGER,
    adj_close   REAL,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, date)
);

CREATE TABLE fundamentals (
    id                           INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol                       TEXT UNIQUE NOT NULL,
    -- Value metrics
    pe_ratio                     REAL,
    pb_ratio                     REAL,
    ev_ebitda                    REAL,
    fcf_yield                    REAL,
    -- Quality / profitability
    roe                          REAL,
    roic                         REAL,
    debt_equity                  REAL,
    gross_margin                 REAL,
    fcf_margin                   REAL,
    -- Growth
    revenue_cagr_3y              REAL,
    eps_cagr_3y                  REAL,
    revenue_cagr_5y              REAL,
    eps_growth_5y                REAL,
    peg_ratio                    REAL,
    -- Income
    dividend_yield               REAL,
    payout_ratio                 REAL,
    dividend_cagr_5y             REAL,
    consecutive_div_growth_years INTEGER,
    earnings_coverage_ratio      REAL,
    -- Classification
    sector                       TEXT,
    industry                     TEXT,
    sector_pe_median             REAL,  -- peer comparison
    sector_ev_ebitda_median      REAL,
    -- Cache control
    updated_at                   TIMESTAMP NOT NULL
);

-- ============================================================
-- Intelligence Layer
-- ============================================================

CREATE TABLE signals (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol      TEXT NOT NULL,
    strategy    TEXT NOT NULL,   -- momentum, value, growth, long_term, quality,
                                 -- dividend_growth, mean_reversion, hybrid:{name}
    signal      TEXT NOT NULL,   -- BUY, SELL, HOLD
    confidence  INTEGER NOT NULL CHECK(confidence BETWEEN 0 AND 100),
    reasoning   TEXT,            -- human-readable explanation
    key_metrics TEXT,            -- JSON blob of input metrics used
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at  TIMESTAMP
);

CREATE TABLE user_preferences (
    id                      INTEGER PRIMARY KEY DEFAULT 1,  -- single row
    investment_horizon      TEXT DEFAULT 'long',            -- short, medium, long
    risk_tolerance          TEXT DEFAULT 'moderate',        -- conservative, moderate, aggressive
    max_single_position_pct REAL DEFAULT 10.0,
    max_sector_pct          REAL DEFAULT 25.0,
    preferred_strategies    TEXT DEFAULT '["quality","long_term","growth"]',  -- JSON array
    hybrid_profiles         TEXT DEFAULT '[]',  -- JSON array of HybridProfile objects
    tax_sensitive           BOOLEAN DEFAULT 0,
    min_confidence_to_act   INTEGER DEFAULT 60,
    scale_in_enabled        BOOLEAN DEFAULT 1,
    scale_in_tranches       INTEGER DEFAULT 3,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE recommendations (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol               TEXT NOT NULL,
    action               TEXT NOT NULL,   -- BUY, ADD, TRIM, SELL, HOLD, WATCH
    urgency              TEXT NOT NULL,   -- high, medium, low
    suggested_size_pct   REAL,            -- % of portfolio to invest/divest
    suggested_tranche    INTEGER,         -- e.g. 1 (this is tranche 1 of N)
    total_tranches       INTEGER,         -- total tranches in scale-in/out plan
    timing_note          TEXT,            -- e.g. "Earnings in 8 days — wait"
    rationale            TEXT NOT NULL,   -- Claude-generated full reasoning
    conflicting_signals  TEXT,            -- JSON array of strategy names that disagree
    supporting_strategies TEXT,           -- JSON array of strategies that agree
    risk_factors         TEXT,            -- JSON array of risk strings
    model_used           TEXT,            -- which Claude model generated this
    created_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at           TIMESTAMP NOT NULL
);

-- ============================================================
-- Watchlist & Research
-- ============================================================

CREATE TABLE watchlist (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol        TEXT UNIQUE NOT NULL,
    added_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes         TEXT,
    target_price  REAL,
    alert_enabled BOOLEAN DEFAULT 0
);

CREATE TABLE research_cache (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol        TEXT NOT NULL,
    briefing_type TEXT NOT NULL,  -- holding_brief, watchlist_analysis
    content       TEXT NOT NULL,  -- full markdown briefing
    model         TEXT NOT NULL,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at    TIMESTAMP NOT NULL,
    UNIQUE(symbol, briefing_type)
);

-- ============================================================
-- Operations
-- ============================================================

CREATE TABLE sync_log (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    sync_type        TEXT NOT NULL,   -- positions, transactions, balances, market_data
    status           TEXT NOT NULL,   -- success, failed, partial
    started_at       TIMESTAMP NOT NULL,
    completed_at     TIMESTAMP,
    records_updated  INTEGER DEFAULT 0,
    error_message    TEXT
);
```

---

## REST API Endpoints

### Portfolio
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/portfolio/summary` | Total value, day P&L, cash, buying power |
| GET | `/api/portfolio/positions` | All positions with current prices + P&L |
| GET | `/api/portfolio/position/{symbol}` | Single position detail + transaction history |
| GET | `/api/portfolio/transactions` | Paginated transaction history |
| GET | `/api/portfolio/performance` | Return vs SPY benchmark |
| POST | `/api/portfolio/sync` | Trigger manual IBKR sync |

### Market
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/market/quote/{symbol}` | Current quote (cached 60s) |
| GET | `/api/market/history/{symbol}` | OHLCV data; query params: `period`, `interval` |
| GET | `/api/market/fundamentals/{symbol}` | Fundamentals (cached 6h) |

### Signals
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/signals` | All current raw strategy signals |
| GET | `/api/signals/{symbol}` | Signals for one symbol |
| POST | `/api/signals/refresh` | Recompute all signals now |

### Recommendations
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/recommendations` | All current smart recommendations |
| GET | `/api/recommendations/{symbol}` | Recommendation for one symbol |
| POST | `/api/recommendations/refresh` | Rerun AI recommendation engine |

### Research
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/research/{symbol}` | Cached AI briefing (24h TTL) |
| POST | `/api/research/{symbol}/refresh` | Force refresh briefing |

### Preferences
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/preferences` | User investment preferences |
| PUT | `/api/preferences` | Update preferences (triggers recommendation refresh) |

### Watchlist
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/watchlist` | All watchlist items with signals + recommendations |
| POST | `/api/watchlist` | Add symbol: `{ symbol, notes?, target_price? }` |
| DELETE | `/api/watchlist/{symbol}` | Remove from watchlist |

### System
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | `{ status, ibkr_connected, last_sync }` |
| GET | `/api/sync/status` | Recent sync log entries |

---

## MCP Server Design

Three standalone MCP servers for use with Claude Desktop or custom agents. All use stdio transport.

### `portfolioiq-portfolio`
Run: `uv run python -m backend.mcp.portfolio_server`

| Tool | Input | Output |
|------|-------|--------|
| `get_portfolio_summary` | — | Net value, day P&L, cash, allocation % |
| `get_positions` | `sector?: string` | Positions array, optional sector filter |
| `get_position` | `symbol: string` | Full position detail |
| `get_transactions` | `symbol?: string, limit?: int` | Transaction history |
| `get_worst_performers` | `n?: int` | Bottom N by unrealized P&L % |
| `get_best_performers` | `n?: int` | Top N by unrealized P&L % |
| `get_recommendations` | `action?: string` | Smart recommendations, optional action filter |

### `portfolioiq-market`
Run: `uv run python -m backend.mcp.market_server`

| Tool | Input | Output |
|------|-------|--------|
| `get_quote` | `symbol: string` | Price, change %, volume |
| `get_history` | `symbol: string, period?: string` | OHLCV summary |
| `get_fundamentals` | `symbol: string` | P/E, P/B, ROE, growth metrics |
| `compare_fundamentals` | `symbols: string[]` | Side-by-side comparison table |

### `portfolioiq-research`
Run: `uv run python -m backend.mcp.research_server`

| Tool | Input | Output |
|------|-------|--------|
| `get_research_briefing` | `symbol: string` | Cached Claude briefing |
| `search_news` | `query: string, limit?: int` | Recent headlines |
| `get_strategy_signals` | `symbol: string` | All strategy signals for symbol |

### Claude Desktop config (`.claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "portfolioiq-portfolio": {
      "command": "uv",
      "args": ["run", "python", "-m", "backend.mcp.portfolio_server"],
      "cwd": "C:/Users/rohit/PycharmProjects/PortfolioIQ"
    },
    "portfolioiq-market": {
      "command": "uv",
      "args": ["run", "python", "-m", "backend.mcp.market_server"],
      "cwd": "C:/Users/rohit/PycharmProjects/PortfolioIQ"
    },
    "portfolioiq-research": {
      "command": "uv",
      "args": ["run", "python", "-m", "backend.mcp.research_server"],
      "cwd": "C:/Users/rohit/PycharmProjects/PortfolioIQ"
    }
  }
}
```

---

## Caching Strategy

| Data | TTL | Storage |
|------|-----|---------|
| Real-time quotes | 60s (market hours), 15min (after hours) | SQLite `market_data` |
| OHLCV daily bars | 24 hours | SQLite `market_data` |
| Fundamentals | 6 hours | SQLite `fundamentals` |
| Research briefings | 24 hours | SQLite `research_cache` |
| Strategy signals | Expire after next refresh or 24h | SQLite `signals` |
| AI recommendations | Expire after preferences change or 4h | SQLite `recommendations` |

---

## Testing Strategy

### Approach
TDD: tests are written alongside each implementation task and committed together.

### Test Types
| Type | Scope | Tools |
|------|-------|-------|
| Unit | Strategies, services, utilities | pytest-asyncio, mock/patch |
| Integration | FastAPI endpoints + DB | FastAPI TestClient, in-memory SQLite |
| Smoke | App start, health endpoint | pytest |

### Directory Structure
```
tests/
├── conftest.py              # shared fixtures (DB session, mock clients)
├── test_models.py           # model import + basic CRUD smoke tests
├── strategies/
│   ├── test_momentum.py
│   ├── test_value.py
│   ├── test_growth.py
│   ├── test_long_term.py
│   ├── test_quality.py
│   ├── test_dividend_growth.py
│   ├── test_mean_reversion.py
│   └── test_hybrid.py
├── routers/
│   ├── test_portfolio.py
│   ├── test_market.py
│   ├── test_signals.py
│   ├── test_recommendations.py
│   └── test_preferences.py
└── services/
    ├── test_market_data.py
    └── test_recommendation_engine.py
```

### Key Fixtures (`tests/conftest.py`)
- `db_session` — async SQLAlchemy session using in-memory SQLite (`sqlite+aiosqlite:///:memory:`)
- `test_client` — FastAPI `AsyncClient` with test DB injected via dependency override
- `mock_ibkr` — `AsyncMock` of `IBKRClient`
- `mock_yfinance` — `unittest.mock.patch` on `yfinance.Ticker` returning fixture DataFrames/dicts
- `mock_claude` — `AsyncMock` of `AsyncAnthropic.messages.create` returning fixture JSON

### Run Commands
```bash
uv run pytest                      # all tests
uv run pytest tests/strategies/    # strategies only
uv run pytest tests/routers/       # API integration tests
uv run pytest -v --tb=short        # verbose with short tracebacks
uv run pytest --co -q              # list tests without running
```

### Mocking Conventions
- Use `unittest.mock.patch` and `AsyncMock` for external I/O (IBKR, yfinance, Claude API)
- Never call real external APIs in tests — always mock at the service boundary
- Use `pytest-httpx` for mocking httpx-based calls if needed
- Strategy unit tests provide synthetic OHLCV DataFrames and fundamentals dicts directly

Market hours detection: 9:30 AM – 4:00 PM ET, Monday–Friday, excluding US market holidays.
