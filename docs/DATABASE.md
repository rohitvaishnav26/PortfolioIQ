# PortfolioIQ — Database Reference

## 1. Overview

- **File location:** `portfolioiq.db` in project root (gitignored)
- **Engine:** SQLite 3 via `aiosqlite` at runtime; plain `sqlite3` for migrations and CLI access
- **Tables:** 11 user tables + `alembic_version` (managed by Alembic)
- **Async URL** (runtime): `sqlite+aiosqlite:///./portfolioiq.db`
- **Sync URL** (migrations/CLI tools): `sqlite:///./portfolioiq.db`

---

## 2. Connecting

### SQLite CLI (quickest for ad-hoc queries)

```bash
sqlite3 portfolioiq.db
.tables                          # list all tables
.schema positions                # show CREATE TABLE
.mode column
.headers on
SELECT * FROM positions LIMIT 5;
.quit
```

### Python sqlite3 (scripts and one-off queries)

```python
import sqlite3
conn = sqlite3.connect("portfolioiq.db")
conn.row_factory = sqlite3.Row   # access columns by name
cur = conn.cursor()
rows = cur.execute("SELECT symbol, shares, market_value FROM positions").fetchall()
for r in rows:
    print(r["symbol"], r["shares"])
conn.close()
```

### SQLAlchemy async (how service code uses it — available after TASK-005)

```python
from sqlalchemy import select
from backend.database import get_session
from backend.models import Position

async with get_session() as session:
    result = await session.execute(select(Position))
    positions = result.scalars().all()
```

### GUI tools

- **DB Browser for SQLite** (https://sqlitebrowser.org) — open `portfolioiq.db`
- **DBeaver** — add a SQLite connection and point it at `portfolioiq.db`

---

## 3. Schema Reference

### `positions` — IBKR holdings

Stores current open positions synced from Interactive Brokers.

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | Primary key |
| symbol | TEXT | Ticker symbol |
| account | TEXT | IBKR account number |
| shares | REAL | Number of shares held |
| avg_cost | REAL | Average cost basis per share |
| current_price | REAL | Last known price |
| market_value | REAL | shares × current_price |
| unrealized_pnl | REAL | Unrealized profit/loss |
| unrealized_pnl_pct | REAL | Unrealized P&L as percentage |
| updated_at | DATETIME | Last sync timestamp |

**Unique constraint:** `(symbol, account)`

```sql
SELECT symbol, shares, avg_cost, market_value, unrealized_pnl_pct
FROM positions ORDER BY market_value DESC;
```

---

### `transactions` — trade history

Historical record of executed trades from IBKR.

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | Primary key |
| ibkr_trade_id | TEXT | Unique trade ID from IBKR |
| symbol | TEXT | Ticker symbol |
| account | TEXT | IBKR account number |
| action | TEXT | BUY or SELL |
| shares | REAL | Number of shares traded |
| price | REAL | Execution price per share |
| commission | REAL | Brokerage commission |
| amount | REAL | Total transaction value |
| trade_date | DATETIME | When the trade executed |

**Unique constraint:** `ibkr_trade_id`

```sql
SELECT trade_date, action, shares, price, commission, amount
FROM transactions WHERE symbol = 'AAPL'
ORDER BY trade_date DESC;
```

---

### `account_summary` — account balances

Current snapshot of account-level financials. One row per account.

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | Primary key |
| account | TEXT | IBKR account number |
| net_liquidation | REAL | Total account value |
| total_cash | REAL | Cash balance |
| buying_power | REAL | Available buying power |
| day_pnl | REAL | Today's profit/loss |
| unrealized_pnl | REAL | Total unrealized P&L |
| realized_pnl | REAL | Total realized P&L (YTD) |
| updated_at | DATETIME | Last sync timestamp |

**Unique constraint:** `account`

```sql
SELECT account, net_liquidation, day_pnl, buying_power, updated_at
FROM account_summary;
```

---

### `market_data` — OHLCV daily bars

Daily price and volume data for tracked symbols, used as the quote cache.

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | Primary key |
| symbol | TEXT | Ticker symbol |
| date | DATE | Trading date |
| open | REAL | Opening price |
| high | REAL | Daily high |
| low | REAL | Daily low |
| close | REAL | Closing price |
| volume | INTEGER | Daily volume |
| updated_at | DATETIME | When this row was fetched |

**Unique constraint:** `(symbol, date)`

```sql
SELECT date, open, high, low, close, volume
FROM market_data WHERE symbol = 'AAPL'
ORDER BY date DESC LIMIT 30;
```

---

### `fundamentals` — valuation and growth metrics

Fundamental data per symbol (P/E, revenue growth, margins, etc.).

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | Primary key |
| symbol | TEXT | Ticker symbol |
| pe_ratio | REAL | Price-to-earnings ratio |
| forward_pe | REAL | Forward P/E estimate |
| peg_ratio | REAL | Price/earnings-to-growth |
| price_to_book | REAL | Price-to-book ratio |
| price_to_sales | REAL | Price-to-sales ratio |
| revenue_growth | REAL | YoY revenue growth rate |
| earnings_growth | REAL | YoY earnings growth rate |
| profit_margin | REAL | Net profit margin |
| roe | REAL | Return on equity |
| debt_to_equity | REAL | Debt-to-equity ratio |
| current_ratio | REAL | Current ratio |
| sector | TEXT | GICS sector |
| industry | TEXT | Industry classification |
| market_cap | REAL | Market capitalization |
| beta | REAL | Beta vs. market |
| dividend_yield | REAL | Annual dividend yield |
| updated_at | DATETIME | Last fetch timestamp |

**Unique constraint:** `symbol` (~25 columns total; abbreviated above)

```sql
SELECT symbol, pe_ratio, revenue_growth, profit_margin, market_cap
FROM fundamentals WHERE sector = 'Technology'
ORDER BY market_cap DESC;
```

---

### `signals` — strategy outputs

Raw strategy signals generated by the scoring engine.

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | Primary key |
| symbol | TEXT | Ticker symbol |
| strategy | TEXT | Strategy name (e.g., `momentum`) |
| signal | TEXT | BUY, SELL, or HOLD |
| confidence | INTEGER | 0–100 (CHECK constraint enforced) |
| reasoning | TEXT | Human-readable rationale |
| key_metrics | TEXT | JSON blob of computed metrics |
| expires_at | DATETIME | Signal TTL |
| created_at | DATETIME | Generation timestamp |

```sql
SELECT symbol, strategy, confidence, reasoning
FROM signals WHERE signal = 'BUY' AND confidence >= 70
ORDER BY confidence DESC;
```

---

### `recommendations` — AI SmartRecommendations

Synthesized recommendations produced by the Claude-powered engine.

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | Primary key |
| symbol | TEXT | Ticker symbol |
| action | TEXT | BUY, ADD, TRIM, SELL, or HOLD |
| urgency | TEXT | Urgency tier |
| suggested_size_pct | REAL | Position size as % of portfolio |
| rationale | TEXT | Full AI-generated rationale |
| supporting_strategies | TEXT | JSON list of supporting strategy names |
| conflicting_signals | TEXT | JSON list of conflicting signal descriptions |
| risk_factors | TEXT | JSON list of identified risk factors |
| created_at | DATETIME | Generation timestamp |

```sql
SELECT symbol, action, urgency, suggested_size_pct, rationale
FROM recommendations ORDER BY created_at DESC;
```

---

### `user_preferences` — single-row config

User-level settings and strategy configuration. Always a single row with `id = 1`.

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | Always 1 |
| risk_tolerance | TEXT | conservative / moderate / aggressive |
| investment_horizon | TEXT | short / medium / long |
| preferred_strategies | TEXT | JSON list of active strategy names |
| hybrid_profiles | TEXT | JSON object of weighted strategy blends |
| max_position_size_pct | REAL | Max % of portfolio in one position |
| updated_at | DATETIME | Last update timestamp |

```sql
SELECT risk_tolerance, investment_horizon, max_position_size_pct
FROM user_preferences WHERE id = 1;
```

---

### `watchlist` — symbols under watch

Symbols the user is monitoring but does not necessarily hold.

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | Primary key |
| symbol | TEXT | Ticker symbol |
| notes | TEXT | Optional user notes |
| added_at | DATETIME | When symbol was added |

**Unique constraint:** `symbol`

```sql
SELECT symbol, notes, added_at FROM watchlist ORDER BY added_at DESC;
```

---

### `research_cache` — Claude briefings

Cached AI-generated research briefs with a TTL to avoid redundant API calls.

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | Primary key |
| symbol | TEXT | Ticker symbol |
| briefing_type | TEXT | Type of briefing (e.g., `earnings`) |
| content | TEXT | Full briefing text |
| expires_at | DATETIME | Cache expiry timestamp |
| created_at | DATETIME | Generation timestamp |

**Unique constraint:** `(symbol, briefing_type)`

```sql
SELECT symbol, briefing_type, expires_at
FROM research_cache WHERE expires_at > datetime('now');
```

---

### `sync_log` — audit trail

Records each sync job execution for monitoring and debugging.

| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER | Primary key |
| sync_type | TEXT | ibkr_positions, market_data, etc. |
| status | TEXT | success or error |
| started_at | DATETIME | Job start time |
| completed_at | DATETIME | Job end time |
| records_updated | INTEGER | Rows inserted or updated |
| error_message | TEXT | Error detail if status = error |

```sql
SELECT sync_type, status, started_at, records_updated, error_message
FROM sync_log ORDER BY started_at DESC LIMIT 5;
```

---

## 4. Working with JSON Columns

The following columns store JSON as TEXT: `signals.key_metrics`, `recommendations.supporting_strategies`, `recommendations.conflicting_signals`, `recommendations.risk_factors`, `user_preferences.preferred_strategies`, `user_preferences.hybrid_profiles`.

### SQLite CLI (SQLite 3.38+ json_each / json_extract)

```sql
SELECT symbol, json_extract(key_metrics, '$.rsi') AS rsi
FROM signals WHERE strategy = 'momentum';
```

### Python sqlite3

```python
import json
cur.execute("SELECT symbol, key_metrics FROM signals")
for row in cur.fetchall():
    metrics = json.loads(row["key_metrics"] or "{}")
    print(row["symbol"], metrics.get("rsi"))
```

### SQLAlchemy async (after TASK-005)

```python
import json
from sqlalchemy import select
from backend.models import Signal

result = await session.execute(select(Signal).where(Signal.strategy == "momentum"))
for sig in result.scalars():
    metrics = json.loads(sig.key_metrics or "{}")
```

---

## 5. Common Queries (Cheat Sheet)

```sql
-- All current positions with unrealized P&L
SELECT symbol, shares, avg_cost, current_price, unrealized_pnl, unrealized_pnl_pct
FROM positions ORDER BY market_value DESC;

-- Latest account balance
SELECT account, net_liquidation, day_pnl, buying_power, updated_at
FROM account_summary;

-- All BUY signals above 70% confidence
SELECT symbol, strategy, confidence, reasoning
FROM signals WHERE signal = 'BUY' AND confidence >= 70
ORDER BY confidence DESC;

-- Latest recommendation per symbol
SELECT symbol, action, urgency, suggested_size_pct, rationale
FROM recommendations ORDER BY created_at DESC;

-- Recent OHLCV for a symbol (last 30 days)
SELECT date, open, high, low, close, volume
FROM market_data WHERE symbol = 'AAPL'
ORDER BY date DESC LIMIT 30;

-- All BUY transactions for a symbol
SELECT trade_date, shares, price, commission, amount
FROM transactions WHERE symbol = 'AAPL' AND action = 'BUY'
ORDER BY trade_date DESC;

-- Last 5 sync operations
SELECT sync_type, status, started_at, records_updated, error_message
FROM sync_log ORDER BY started_at DESC LIMIT 5;

-- Expired signals (for cleanup reference)
SELECT symbol, strategy, expires_at FROM signals
WHERE expires_at < datetime('now');
```

---

## 6. Alembic — Managing Migrations

```bash
# Check current migration state
uv run alembic current

# Apply all pending migrations
uv run alembic upgrade head

# Roll back one migration
uv run alembic downgrade -1

# Generate a new migration after model changes
uv run alembic revision --autogenerate -m "add column x to positions"

# Show migration history
uv run alembic history --verbose
```

Migration files live in `alembic/versions/`. The `alembic_version` table in SQLite tracks which revision is currently applied.

---

## Critical Files

| File | Role |
|------|------|
| `portfolioiq.db` | SQLite database file (project root, gitignored) |
| `alembic.ini` | Alembic config; sets `sqlalchemy.url = sqlite:///./portfolioiq.db` |
| `alembic/env.py` | Migration runner; imports `Base` and `settings` |
| `alembic/versions/fd301443d352_initial.py` | Initial migration — creates all 11 tables |
| `backend/models/__init__.py` | Re-exports all 12 ORM model classes |
| `backend/config.py` | `settings.database_url = "sqlite+aiosqlite:///./portfolioiq.db"` |
