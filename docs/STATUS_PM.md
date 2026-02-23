# PortfolioIQ — Product Status Brief
**Audience:** Product Manager / Product Owner
**Last updated:** February 21, 2026 (post TASK-006)

---

## What Is PortfolioIQ?

PortfolioIQ is a personal investment portfolio monitor and AI-powered recommendation engine that runs entirely on your own machine.

It connects to your Interactive Brokers (IBKR) brokerage account, automatically pulls in your holdings and trade history, runs multiple investment analysis strategies against your portfolio, and then uses Claude AI to synthesise everything into plain-English, actionable buy/sell/hold recommendations.

**The core promise:** A private, intelligent dashboard that tells you *what to do with your portfolio and why* — no subscriptions, no data leaving your machine, no generic advice.

---

## Who Is This For?

A self-directed investor who:
- Uses Interactive Brokers as their brokerage
- Wants data-driven signals but also wants to understand the reasoning, not just a score
- Values privacy — their portfolio data should never touch a third-party cloud
- Wants their portfolio analysis to reflect *their* investment style (growth-focused, income-focused, long-term compounder, etc.)

---

## What Does the Finished Product Look Like?

When fully built, you open a browser to `localhost:5173` and see:

| Screen | What You See |
|--------|-------------|
| **Dashboard** | Total portfolio value, day P&L, cash balance, sector allocation chart |
| **Portfolio** | Table of all IBKR positions with live prices, cost basis, unrealised gain/loss |
| **Signals** | Per-strategy buy/sell/hold signals for every holding (momentum, value, growth, etc.) |
| **Recommendations** | AI-generated cards: "ADD to AMZN — Scale in tranche 2 of 3. Cloud growth intact, current dip is macro-driven not fundamental." |
| **Settings** | Your investment profile — risk tolerance, preferred strategies, max position size, etc. |

All data updates automatically every 5 minutes via your live IBKR connection.

---

## Progress: Where Are We Now?

### Completed (Foundation Layer)

| What Was Done | Why It Matters |
|---------------|----------------|
| **Project scaffold** — all folders, config files, frontend/backend structure set up | The skeleton everything else builds on. Means any developer can clone the repo and get oriented immediately. |
| **Dependencies installed** — Python packages (FastAPI, SQLAlchemy, IBKR library, AI SDK, etc.) and frontend packages (React, charts, UI components) | Without this, nothing runs. The specific choices (pure-Python data libraries, local SQLite) ensure the app works on Windows without complex C-compiler setup. |
| **Test infrastructure** — shared test fixtures that mock external services | Means every feature built from here can be tested without a live IBKR connection or real API calls. Reduces risk of regressions. |
| **Database models** — all 12 database tables defined | The full data structure of the app now exists. Every piece of data the app needs — positions, transactions, signals, recommendations, preferences — has a defined home. This is the schema the whole product runs on. |
| **Database migrations + app config** — Alembic wired to all 12 models; `portfolioiq.db` created on disk with all tables | The actual database file now exists and is versioned. Any future schema change is a controlled migration, not a manual SQL script. The app config layer (`backend/config.py`) is also in place, reading all settings from `.env`. |
| **FastAPI skeleton + health endpoint** — backend server starts, responds to requests, CORS enabled for the frontend | The backend is now a running service. A developer can start it with one command and hit `GET /api/health` to confirm it's alive. All Layer 2 data endpoints will build on this foundation. |
| **IBKR connection manager** — `IBKRClient` class handles connect, disconnect, and retry logic | The app can now establish and recover from IBKR connections. All sync services (positions, transactions, balances) will use this as their gateway to IBKR data. |

**Layer 1 complete. Layer 2 is underway — 1 of 8 tasks done.**

---

## What Has Been Defined (But Not Yet Built)

The following are fully *designed and documented* but not yet coded:

- **7 investment strategy engines** (Momentum, Value, Dividend Growth, Mean Reversion, Quality, Growth, Long-Term Compounder) — each has defined buy/sell/hold rules and a confidence scoring formula
- **AI Recommendation Engine** — the Claude-powered layer that synthesises signals + your preferences into a SmartRecommendation with action, urgency, position sizing, and rationale
- **Hybrid strategy profiles** — user-configurable blends (e.g. "60% Growth + 40% Long-Term Compounder") with a holding bias setting
- **All REST API endpoints** — 30+ endpoints across portfolio, market data, signals, recommendations, preferences, and watchlist
- **Full React frontend** — 5 screens with dark theme, interactive charts, and real-time data

---

## What's Being Built Next (In Order)

### ~~Step 4 — Database Migrations (TASK-004)~~ ✅ Complete
Alembic is set up and the initial migration has been applied. `portfolioiq.db` exists on disk with all 12 tables. All future schema changes will be versioned migrations.

### ~~Step 5 — FastAPI Skeleton + Health Check (TASK-005)~~ ✅ Complete
`backend/database.py` and `backend/main.py` are implemented. The server starts with `uv run uvicorn backend.main:app --reload --port 8000` and `GET /api/health` returns `{"status":"ok","version":"0.1.0"}`. 13/13 tests pass.

### Steps 6–13 — IBKR Sync + Market Data + API (Layer 2)
The app connects to IBKR, pulls positions and transactions, fetches live market data and fundamentals from Yahoo Finance, and exposes all of it via REST endpoints. **After this: a developer can query real portfolio data via API.**

- ~~TASK-006: IBKR Connection Manager~~ ✅ Complete
- TASK-007: Position Sync — next up
- TASK-008 through TASK-013: pending

### Steps 14–18 — Strategy Engine + AI Recommendations (Layer 3)
The 7 strategies run against real portfolio data, generate signals, and the Claude-powered recommendation engine synthesises them into actionable advice. **After this: the intelligence layer is live.**

### Steps 19–27 — Frontend (Layer 4)
The React dashboard is built out — all 5 screens, charts, tables, recommendation cards. **After this: the full product is usable in a browser.**

---

## Key Milestones — When Can You See/Test the App?

| Milestone | After Task | What You Can Do |
|-----------|-----------|-----------------|
| **Backend health check** | TASK-005 ✅ | Run the server; confirm it starts and responds |
| **Real data in API** | TASK-013 | Query your actual IBKR positions via API or Swagger UI — no frontend yet |
| **App shell loads** | TASK-021 | Browser opens; dark-themed shell with navigation — placeholder content |
| **First useful dashboard** | TASK-024 | Full dashboard with real holdings, live prices, charts — **first real product experience** |
| **Complete P0** | TASK-027 | All 5 screens live, AI recommendations working, preferences configurable |

---

## Risks and Dependencies

| Risk | Impact | Mitigation |
|------|--------|-----------|
| IBKR TWS must be running locally | Without it, no position data syncs | All tests mock the IBKR connection; manual testing requires TWS open |
| Anthropic API key required for AI recommendations | Recommendations layer won't work without it | Key configured via `.env` file; strategies run independently without it |
| yfinance rate limits (~2,000 req/hour) | Bulk fundamentals fetch for large portfolios could be throttled | 6-hour cache on fundamentals; 0.5s delay between bulk calls |
| Windows environment | Some Python data-science libraries have C compilation issues on Windows | pandas-ta chosen specifically because it's pure Python (avoids this issue) |

---

## What Makes This Different From a Bloomberg Terminal or Robinhood?

| Dimension | PortfolioIQ | Typical Tool |
|-----------|-------------|-------------|
| Data privacy | 100% local — nothing leaves your machine | Cloud-stored, often sold |
| Customisation | Your strategies, your weights, your preferences | Generic one-size-fits-all |
| Reasoning | Claude explains *why* in plain English | Score or percentage with no context |
| Cost | One-time setup + Anthropic API calls (pennies per analysis) | $30–$600/month subscriptions |
| Brokerage lock-in | IBKR only (v1) | Platform-specific |

---

## Definition of "Done" for This Iteration

The iteration is complete when:
1. The backend server starts and connects to IBKR
2. Positions, transactions, and balances sync automatically every 5 minutes
3. All 7 strategies generate buy/sell/hold signals for every holding
4. The AI recommendation engine produces a SmartRecommendation for every position
5. The React dashboard displays all of the above in a browser
6. Settings screen allows preferences to be saved and triggers recommendation refresh
7. All tests pass with no real external API calls
