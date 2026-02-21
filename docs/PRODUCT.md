# PortfolioIQ — Product Specification

## Vision

PortfolioIQ gives self-directed investors running Interactive Brokers accounts a local, private tool that:
1. Automatically syncs their full portfolio — no manual exports
2. Shows a clear, real-time picture of performance and allocation
3. Generates intelligent, context-aware buy/sell/hold recommendations using AI
4. Explains its reasoning in plain language

Everything runs locally. No data leaves the machine.

---

## User Persona

**Primary:** Rohit — experienced investor with an IBKR account, holds a diversified stock portfolio across multiple sectors, prefers a long-term compounding approach but also wants to catch momentum opportunities and flag when fundamentals deteriorate. Technical enough to run a local Python backend. Values privacy, speed, and intelligence over manual spreadsheet tracking.

---

## P0 — Must Have for v1

These features are required before the app is considered usable.

### P0-01: IBKR Auto-Connect & Data Sync

**User story:** As an investor, I want my portfolio data to automatically stay in sync with IBKR so I never have to export CSV files or manually update anything.

**Acceptance criteria:**
1. Application connects to IBKR TWS/Gateway on startup (port 4002 paper, 4001 live) via ib_insync
2. On first connect, performs a full sync of positions, transactions (last 90 days), and account balances
3. Background sync runs every 5 minutes automatically while the app is running
4. Last sync time and status is visible in the UI
5. If IBKR connection drops, app logs the error, retries with exponential backoff, and shows a connection status indicator
6. Manual sync trigger available: `POST /api/portfolio/sync` and a "Sync Now" button in UI

**UI notes:** Connection status badge (green/red) in the app header. Last sync timestamp next to it.

---

### P0-02: Portfolio Dashboard

**User story:** As an investor, I want to see my full portfolio at a glance — total value, today's P&L, and a breakdown of all my positions — so I can quickly assess where I stand.

**Acceptance criteria:**
1. Summary cards show: Total Portfolio Value, Day P&L ($ and %), Total Unrealized P&L ($ and %), Cash Balance
2. P&L values are color-coded: green for positive, red for negative
3. Positions table shows all holdings with: Symbol, Company Name, Sector, Shares, Avg Cost, Current Price, Market Value, Unrealized P&L ($), Unrealized P&L (%)
4. Table is sortable by any column
5. Sector allocation donut chart shows portfolio weight by sector
6. Clicking a position row opens a detail panel with: transaction history, price chart, current signals

**UI notes:** Dark fintech theme. Cards use subtle border glow on positive P&L. Positions table uses monospace font for numbers. Sector chart uses a muted color palette.

---

### P0-03: Auto-Refreshing Market Data

**User story:** As an investor, I want current prices to update automatically so the dashboard always shows live data without me refreshing the browser.

**Acceptance criteria:**
1. Prices refresh every 60 seconds during market hours (9:30 AM – 4:00 PM ET)
2. After market hours, refresh interval extends to 15 minutes
3. A "last updated" timestamp shows when prices were last fetched
4. If a price fetch fails, the last known price is shown with a staleness indicator
5. Position P&L values update whenever prices refresh

**UI notes:** Subtle pulse animation on price cells when they update.

---

### P0-04: Buy/Sell Signals — Momentum & Value

**User story:** As an investor, I want to see buy/sell/hold signals for each of my holdings based on technical and fundamental criteria, so I have data-driven input for my decisions.

**Acceptance criteria:**
1. Signals are computed for all current positions using Momentum strategy (RSI, MACD, 200-day SMA, 52-week high proximity)
2. Signals are computed using Value strategy (P/E vs sector median, FCF yield, EV/EBITDA)
3. Each signal shows: strategy name, signal (BUY/SELL/HOLD), confidence score (0–100), and key metrics used
4. Signals page shows all signals grouped by symbol or by strategy (user-selectable view)
5. Manual refresh: `POST /api/signals/refresh` and "Refresh Signals" button in UI
6. Signals auto-refresh after each IBKR sync

**UI notes:** BUY = green badge, SELL = red badge, HOLD = gray badge. Confidence shown as a progress bar under the badge.

---

## P1 — Next Iteration

These features make the product significantly more powerful.

### P1-01: Full Strategy Suite

**User story:** As an investor, I want signals from multiple investment strategies so I can see which approach supports or contradicts a trade.

**Strategies to add:**
- Dividend Growth (yield, payout ratio, 5yr CAGR, consecutive growth years)
- Mean Reversion (Bollinger Bands, RSI extremes, 50-day SMA distance)
- Quality (ROE, ROIC, debt/equity, earnings consistency)
- Growth (revenue CAGR, EPS CAGR, PEG ratio, gross margin)
- Long-Term Compounder (ROE consistency, FCF margin, P/FCF — strong HOLD bias)

**Acceptance criteria:**
1. All 7 strategies compute signals for all positions
2. Strategy comparison view shows all strategies side by side for a given symbol in a grid
3. Each strategy's parameters are configurable from the Settings page (e.g., change RSI thresholds)
4. Strategy configs are persisted in user_preferences

---

### P1-02: Hybrid Strategy Profiles

**User story:** As an investor, I want to define my own investment approach by blending multiple strategies — for example, "buy growth stocks and hold long-term" — so recommendations align with how I actually invest.

**Acceptance criteria:**
1. User can create hybrid profiles with a name, strategy weights, and a holding bias (short/medium/long)
2. Holding bias `long` suppresses technical sell signals — only fundamental deterioration triggers SELL
3. Hybrid profiles appear alongside individual strategies in the signals view
4. At least 3 preset profiles available: "Growth + Long-Term", "Income & Value", "Balanced"
5. Profiles configurable in Settings page

---

### P1-03: AI Smart Recommendation Engine

**User story:** As an investor, I want AI-driven recommendations that consider my full portfolio context, personal preferences, and market conditions — not just raw signals — so I get actionable, nuanced guidance.

**Acceptance criteria:**
1. For each position, Claude (claude-sonnet-4-5) synthesizes:
   - All strategy signals + confidence scores
   - Current portfolio weight and sector concentration
   - Available cash and buying power
   - User preferences (horizon, risk tolerance, max position size, tax sensitivity)
   - Market conditions (broad market trend, VIX level)
2. Output action is one of: BUY, ADD, TRIM, SELL, HOLD, WATCH
3. Recommendation includes: urgency (high/medium/low), suggested position size %, scale-in tranche info, timing note, full rationale, conflicting signals, risk factors
4. Scale-in logic: if BUY/ADD, recommendation suggests a tranche plan (e.g., "Tranche 1 of 3 — 2% now, wait for pullback confirmation for tranche 2")
5. Tax sensitivity: if enabled and position has short-term unrealized gain, TRIM/SELL recommendations note the tax implication

---

### P1-04: MCP Server for Portfolio Queries

**User story:** As an investor, I want to ask Claude Desktop questions like "What's my tech sector exposure?" or "Show me my worst performers" and get instant answers from my real portfolio data.

**Acceptance criteria:**
1. Three MCP servers implemented: `portfolioiq-portfolio`, `portfolioiq-market`, `portfolioiq-research`
2. Portfolio server tools: get_portfolio_summary, get_positions, get_position, get_transactions, get_worst_performers, get_best_performers, get_recommendations
3. Market server tools: get_quote, get_history, get_fundamentals, compare_fundamentals
4. Research server tools: get_research_briefing, search_news, get_strategy_signals
5. Claude Desktop config documented with correct MCP server paths

---

### P1-05: Research Briefings per Holding

**User story:** As an investor, I want an AI-generated research brief for each of my holdings — including recent news, analyst sentiment, and key risks — so I stay informed without spending an hour per stock.

**Acceptance criteria:**
1. Each holding has a "Research" tab in its detail panel
2. Briefing generated by claude-opus-4-5 with web search enabled
3. Briefing covers: business overview, recent news (last 30 days), key risks, growth catalysts, analyst sentiment summary
4. Briefings cached for 24 hours; refresh button available
5. Daily API call limit (configurable, default 20) enforced to manage costs

---

### P1-06: Performance Tracking & Benchmark Comparison

**User story:** As an investor, I want to see how my portfolio performs against SPY so I know if I'm actually outperforming the market.

**Acceptance criteria:**
1. Performance chart shows portfolio total return vs SPY over selectable periods: 1M, 3M, 6M, YTD, 1Y
2. Summary stats: portfolio return %, SPY return %, alpha, Sharpe ratio (approximate)
3. Per-position return attribution chart showing which holdings contributed most/least

---

### P1-07: Watchlist with Recommendations

**User story:** As an investor, I want to track stocks I'm considering buying, and get the same strategy signals and AI recommendations for them as for my current holdings.

**Acceptance criteria:**
1. Add/remove symbols to watchlist from the Watchlist page
2. All strategy signals computed for watchlist symbols
3. AI recommendations generated for watchlist items (action will be BUY or WATCH)
4. Optional price target — shows % to target and highlights when price is within 5% of target

---

## P2 — Future

These features are valuable but deferred until v1 is proven.

### P2-01: Backtesting Engine
Replay historical data through strategy rules to see how signals would have performed.

### P2-02: MCP Trade Execution Server
Allow agents to place orders via IBKR through the MCP server (with explicit user confirmation step).

### P2-03: Tax Lot Optimization
When trimming a position, suggest which specific tax lots to sell to minimize tax impact.

### P2-04: Dividend Calendar & Income Projections
Calendar view of upcoming dividend ex-dates and projected annual income from current holdings.

### P2-05: Alerts
Push alerts (desktop notification or email) for: price target hit, strategy signal change, earnings date approaching, major news event.

### P2-06: PDF/Markdown Report Export
Generate a formatted portfolio report covering performance, signals, and recommendations.
