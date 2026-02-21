# PortfolioIQ — Integrations Guide

## 1. IBKR TWS API (via ib_insync)

### Overview

PortfolioIQ connects to IBKR using the TWS API via `ib_insync`, an async-friendly Python wrapper. This requires TWS (Trader Workstation) or IB Gateway to be running locally.

### TWS/Gateway Setup

1. **Install TWS or IB Gateway**
   - TWS: full UI, heavier — good for development/testing
   - IB Gateway: headless, lighter — preferred for running as a background service
   - Download from: https://www.interactivebrokers.com/en/trading/tws.php

2. **Enable API Connections in TWS**
   - TWS: Edit → Global Configuration → API → Settings
   - Enable "Enable ActiveX and Socket Clients"
   - Check "Allow connections from localhost only"
   - Uncheck "Read-Only API" if you want order execution (P2 feature)
   - Socket port: `4002` (paper trading) or `4001` (live trading)
   - Set a unique Master Client ID (leave as 0 or set to 1)

3. **Paper Trading**
   - Use paper trading account for development (port 4002)
   - Paper account shows simulated positions; use your live account number format but prepend with `DU`

### Environment Variables
```bash
IBKR_HOST=127.0.0.1
IBKR_TWS_PORT=4002       # 4002=paper, 4001=live
IBKR_CLIENT_ID=1         # must be unique per connection
IBKR_ACCOUNT=U1234567    # your account number
```

### ib_insync Connection Pattern

```python
from ib_insync import IB, util

ib = IB()
await ib.connectAsync(
    host=settings.ibkr_host,
    port=settings.ibkr_tws_port,
    clientId=settings.ibkr_client_id,
    readonly=True,   # set False if placing orders
)
```

### Key ib_insync Calls

| Data | ib_insync Call | Notes |
|------|---------------|-------|
| Positions | `ib.portfolio()` | Returns PortfolioItem list |
| Account balances | `ib.accountSummary()` | Returns AccountValue list |
| Filled orders | `ib.executions()` | Returns Execution list; filter by date |
| Open orders | `ib.trades()` | Returns Trade list |
| Historical OHLCV | `ib.reqHistoricalDataAsync(contract, ...)` | Use for price history |
| Live quotes | `ib.reqMktData(contract)` | Returns Ticker; use snapshot=True for one-time |

### Position Sync Logic

```python
portfolio_items = ib.portfolio()
for item in portfolio_items:
    if item.contract.secType != 'STK':
        continue  # skip options, futures, etc.
    position = {
        "symbol": item.contract.symbol,
        "account": item.account,
        "shares": item.position,
        "avg_cost": item.averageCost,
        "market_value": item.marketValue,
        "unrealized_pnl": item.unrealizedPNL,
        "realized_pnl": item.realizedPNL,
    }
    # upsert into positions table using ON CONFLICT(symbol, account) DO UPDATE
```

### Transaction Sync Logic

```python
from ib_insync import ExecutionFilter
from datetime import datetime, timedelta

# Fetch executions from last 90 days
exec_filter = ExecutionFilter(
    clientId=settings.ibkr_client_id,
    time=(datetime.now() - timedelta(days=90)).strftime("%Y%m%d-%H:%M:%S")
)
executions = await ib.reqExecutionsAsync(exec_filter)
fills = await ib.reqFillsAsync()

for fill in fills:
    txn = {
        "symbol": fill.contract.symbol,
        "account": fill.execution.acctNumber,
        "trade_date": fill.execution.time.date(),
        "action": fill.execution.side,   # BOT / SLD
        "shares": fill.execution.shares,
        "price": fill.execution.price,
        "commission": fill.commissionReport.commission if fill.commissionReport else 0,
        "amount": fill.execution.shares * fill.execution.price,
        "ibkr_trade_id": fill.execution.execId,   # unique, use for deduplication
    }
    # upsert using ON CONFLICT(ibkr_trade_id) DO NOTHING
```

### Reconnect Logic

```python
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=2, max=60)
)
async def connect_with_retry(ib: IB, settings) -> None:
    await ib.connectAsync(
        host=settings.ibkr_host,
        port=settings.ibkr_tws_port,
        clientId=settings.ibkr_client_id,
    )

# Also register disconnected callback
def on_disconnected():
    logger.warning("IBKR disconnected — will retry on next sync cycle")

ib.disconnectedEvent += on_disconnected
```

---

## 2. Market Data — yfinance

### Overview

yfinance is used for:
- Historical OHLCV data (daily bars, used by technical strategy indicators)
- Real-time/delayed quotes during market hours
- Fundamental data (P/E, P/B, ROE, revenue CAGR, dividends, etc.)

All data is cached in SQLite to minimize API calls.

### OHLCV History

```python
import yfinance as yf

ticker = yf.Ticker(symbol)
hist = ticker.history(period="1y", interval="1d", auto_adjust=True)
# Returns DataFrame with: Open, High, Low, Close, Volume, Dividends, Stock Splits
# Index is datetime
```

Cache strategy: fetch if latest entry in `market_data` table is older than 24 hours.

### Current Quote

```python
ticker = yf.Ticker(symbol)
info = ticker.fast_info   # lighter, faster than .info
current_price = info.last_price
market_cap = info.market_cap
```

Cache strategy: serve from `market_data` table if last update < 60s (market hours) or 15 min (after hours).

### Fundamentals

```python
ticker = yf.Ticker(symbol)
info = ticker.info

fundamentals = {
    "pe_ratio": info.get("trailingPE"),
    "pb_ratio": info.get("priceToBook"),
    "ev_ebitda": info.get("enterpriseToEbitda"),
    "roe": info.get("returnOnEquity"),
    "debt_equity": info.get("debtToEquity"),
    "gross_margin": info.get("grossMargins"),
    "dividend_yield": info.get("dividendYield"),
    "payout_ratio": info.get("payoutRatio"),
    "revenue_cagr_3y": None,    # calculated from quarterly data if needed
    "eps_cagr_3y": info.get("earningsGrowth"),
    "sector": info.get("sector"),
    "industry": info.get("industry"),
}
```

Cache strategy: fetch if `fundamentals.updated_at` is older than 6 hours.

### Rate Limiting

yfinance uses Yahoo Finance's public API with no explicit rate limits, but aggressive fetching can result in temporary blocks.

Best practices:
- Batch fetch with `yf.download(symbols_list, ...)` for OHLCV across multiple tickers
- Add 0.5s sleep between individual `ticker.info` calls during bulk fundamental refresh
- Always check cache before fetching

### Sector Peer Medians

For value strategy, sector median P/E and EV/EBITDA are needed. Approach:
- Use the `sector` field from yfinance fundamentals
- Maintain a lookup table (updated weekly) with typical sector medians
- Alternatively, fetch a basket of sector ETF holdings to compute dynamic medians

---

## 3. Claude API

### Overview

The Anthropic Claude API is used in two distinct roles:

| Role | Model | Context |
|------|-------|---------|
| Recommendation Engine | `claude-sonnet-4-5` | Synthesizes signals → SmartRecommendation |
| Research Agent | `claude-opus-4-5` | Deep research with web search per holding |

### SDK Setup

```python
from anthropic import AsyncAnthropic

client = AsyncAnthropic(api_key=settings.anthropic_api_key)
```

### Recommendation Engine Call

```python
response = await client.messages.create(
    model=settings.signal_model,    # claude-sonnet-4-5
    max_tokens=1024,
    system=RECOMMENDATION_SYSTEM_PROMPT,
    messages=[
        {
            "role": "user",
            "content": build_recommendation_prompt(symbol, signals, context, preferences)
        }
    ]
)
# Parse JSON from response.content[0].text
```

The response must be valid JSON matching the `SmartRecommendation` schema. Use a strict system prompt instructing Claude to always return valid JSON. Validate with Pydantic before persisting.

### Research Agent Call (with Web Search)

```python
response = await client.messages.create(
    model=settings.research_model,   # claude-opus-4-5
    max_tokens=4096,
    tools=[{"type": "web_search_20250305", "name": "web_search"}],
    system=RESEARCH_SYSTEM_PROMPT,
    messages=[
        {
            "role": "user",
            "content": f"Research {symbol} ({company_name}). Provide a structured briefing..."
        }
    ]
)
```

### Rate Limiting & Cost Control

```python
# Track daily API calls in sync_log or a dedicated api_usage table
# Check before each call:
today_count = await db.count_api_calls_today(model=settings.research_model)
if today_count >= settings.research_daily_call_limit:
    raise RateLimitError("Daily research API limit reached")
```

Retry logic (for transient errors):
```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from anthropic import APIStatusError

@retry(
    retry=retry_if_exception_type(APIStatusError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def call_claude_with_retry(client, **kwargs):
    return await client.messages.create(**kwargs)
```

### System Prompts

**Recommendation Engine system prompt:**
```
You are a senior portfolio analyst. You analyze investment signals and portfolio context
to generate precise, actionable recommendations. You always:
- Consider the investor's stated preferences and holding horizon
- Account for portfolio concentration risk
- Prefer gradual scaling in/out over all-at-once moves
- Flag timing concerns (earnings, volatility, tax implications)
- Return ONLY valid JSON matching the SmartRecommendation schema
- Never recommend more than 5% of portfolio in a single tranche
```

**Research Agent system prompt:**
```
You are an investment research analyst. When given a stock ticker, search for recent
information and produce a structured briefing covering:
1. Business overview (2-3 sentences)
2. Recent news and developments (last 30 days)
3. Key growth catalysts
4. Key risks and headwinds
5. Analyst sentiment summary (if available)
Keep the briefing factual, concise, and actionable. Format in markdown.
```

---

## 4. MCP Servers

### Overview

Three Model Context Protocol servers expose PortfolioIQ data to external agents and Claude Desktop. All use stdio transport (subprocess, not HTTP).

### Technology

Uses Anthropic's `mcp` Python SDK (version 1.0+).

```python
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

server = Server("portfolioiq-portfolio")

@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="get_portfolio_summary",
            description="Get total portfolio value, day P&L, and allocation breakdown",
            inputSchema={"type": "object", "properties": {}}
        ),
        # ... more tools
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "get_portfolio_summary":
        # query SQLite, return result
        return [TextContent(type="text", text=json.dumps(summary))]

async def main():
    async with stdio_server() as streams:
        await server.run(*streams, server.create_initialization_options())

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### Server Locations

| Server | Module | Description |
|--------|--------|-------------|
| Portfolio | `backend/mcp/portfolio_server.py` | Positions, transactions, recommendations |
| Market | `backend/mcp/market_server.py` | Quotes, history, fundamentals |
| Research | `backend/mcp/research_server.py` | Briefings, news search, signals |

### Claude Desktop Configuration

Add to `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "portfolioiq-portfolio": {
      "command": "uv",
      "args": ["run", "python", "-m", "backend.mcp.portfolio_server"],
      "cwd": "C:\\Users\\rohit\\PycharmProjects\\PortfolioIQ"
    },
    "portfolioiq-market": {
      "command": "uv",
      "args": ["run", "python", "-m", "backend.mcp.market_server"],
      "cwd": "C:\\Users\\rohit\\PycharmProjects\\PortfolioIQ"
    },
    "portfolioiq-research": {
      "command": "uv",
      "args": ["run", "python", "-m", "backend.mcp.research_server"],
      "cwd": "C:\\Users\\rohit\\PycharmProjects\\PortfolioIQ"
    }
  }
}
```

### Tool Schemas — Portfolio Server

```python
# get_positions
{
    "name": "get_positions",
    "description": "Get all portfolio positions with current prices and P&L",
    "inputSchema": {
        "type": "object",
        "properties": {
            "sector": {
                "type": "string",
                "description": "Filter by sector (e.g. 'Technology'). Omit for all."
            }
        }
    }
}

# get_worst_performers
{
    "name": "get_worst_performers",
    "description": "Get the N worst-performing positions by unrealized P&L percentage",
    "inputSchema": {
        "type": "object",
        "properties": {
            "n": {"type": "integer", "default": 5}
        }
    }
}
```

---

## 5. Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `IBKR_HOST` | `127.0.0.1` | TWS/Gateway host |
| `IBKR_TWS_PORT` | `4002` | TWS port (4002=paper, 4001=live) |
| `IBKR_CLIENT_ID` | `1` | Client ID (must be unique per connection) |
| `IBKR_ACCOUNT` | — | IBKR account number |
| `ANTHROPIC_API_KEY` | — | Anthropic API key |
| `DATABASE_URL` | `sqlite+aiosqlite:///./portfolioiq.db` | SQLite connection string |
| `APP_ENV` | `development` | Environment (development/production) |
| `LOG_LEVEL` | `INFO` | Logging level |
| `SYNC_INTERVAL_MINUTES` | `5` | How often to sync IBKR data |
| `QUOTE_REFRESH_SECONDS` | `60` | Quote cache TTL (market hours) |
| `OHLCV_CACHE_TTL_HOURS` | `24` | Daily OHLCV cache TTL |
| `FUNDAMENTAL_CACHE_TTL_HOURS` | `6` | Fundamentals cache TTL |
| `RESEARCH_CACHE_TTL_HOURS` | `24` | Research briefing cache TTL |
| `RESEARCH_DAILY_CALL_LIMIT` | `20` | Max research API calls per day |
| `RESEARCH_MODEL` | `claude-opus-4-5` | Model for research briefings |
| `SIGNAL_MODEL` | `claude-sonnet-4-5` | Model for recommendation engine |
