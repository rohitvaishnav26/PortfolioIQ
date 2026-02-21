# PortfolioIQ — Investment Strategies

This document defines each investment strategy: the data inputs, signal conditions, confidence scoring, and how the output feeds into the AI recommendation engine.

All strategies return a `StrategySignal` with:
- `signal`: `BUY` | `SELL` | `HOLD`
- `confidence`: 0–100 integer
- `reasoning`: human-readable explanation
- `key_metrics`: dict of input values used

---

## Signal Output Schema

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

@dataclass
class StrategySignal:
    symbol: str
    strategy: str                          # strategy identifier
    signal: Literal["BUY", "SELL", "HOLD"]
    confidence: int                        # 0-100
    reasoning: str                         # 1-3 sentence explanation
    key_metrics: dict                      # input values for auditability
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None     # None = expires on next refresh
```

---

## Strategy 1: Momentum (`momentum`)

**Philosophy:** Follow price and volume trends. Buy stocks with strong upward momentum; exit when the trend breaks.

**Timeframe:** Medium-term, 1–6 months typical holding.

**Data requirements:** 200+ days of daily OHLCV data, current volume.

### Signal Inputs
| Input | Calculation | Source |
|-------|-------------|--------|
| RSI | RSI(14) using pandas-ta | OHLCV |
| MACD | MACD(12, 26, 9) — line and signal | OHLCV |
| 52-week proximity | `(close - 52w_low) / (52w_high - 52w_low)` | OHLCV |
| 200-day SMA | Simple moving average | OHLCV |
| 90-day price change | `(close_today - close_90d_ago) / close_90d_ago` | OHLCV |
| Volume ratio | `avg_volume_10d / avg_volume_90d` | OHLCV |

### Default Parameters
```python
RSI_BUY_MIN = 40
RSI_BUY_MAX = 65
RSI_SELL    = 75
PROXIMITY_MIN = 0.75        # near 52-week high (top 25% of 52w range)
MOMENTUM_90D_MIN = 0.05     # +5% over 90 days
VOLUME_RATIO_MIN = 1.2      # 10d avg volume 20% above 90d avg
```

### Signal Logic
**BUY** — must meet 4 or more of the following 6 conditions:
1. RSI between `RSI_BUY_MIN` and `RSI_BUY_MAX`
2. MACD line > MACD signal line
3. 52-week proximity > `PROXIMITY_MIN`
4. Price > 200-day SMA
5. 90-day price change > `MOMENTUM_90D_MIN`
6. Volume ratio > `VOLUME_RATIO_MIN`

**SELL** — any one of:
1. RSI > `RSI_SELL`
2. Price has fallen > 20% below 52-week high (after a BUY was emitted)
3. Price < 200-day SMA for 3 consecutive trading days

**HOLD** — otherwise

### Confidence Score
Each met BUY condition contributes points:
```
RSI in range:            20 pts
MACD line > signal:      15 pts
Proximity > 0.75:        20 pts
Price > 200-day SMA:     15 pts
90d momentum > 5%:       20 pts
Volume ratio > 1.2:      10 pts

Total = sum of met conditions (max 100)
```
For SELL signals, confidence = severity of the triggering condition (e.g., RSI 80 → higher confidence than RSI 76).

---

## Strategy 2: Value (`value`)

**Philosophy:** Buy fundamentally undervalued stocks relative to sector peers. Sell when valuation becomes stretched.

**Timeframe:** Long-term, 12–36 months typical holding.

**Data requirements:** Current fundamentals (P/E, P/B, EV/EBITDA, FCF yield), sector median comparables.

### Signal Inputs
| Input | Description | Source |
|-------|-------------|--------|
| P/E ratio | Price / trailing twelve months EPS | fundamentals |
| Sector P/E median | Median P/E of stocks in same sector | fundamentals |
| FCF yield | Free cash flow / market cap | fundamentals |
| EV/EBITDA | Enterprise value / EBITDA | fundamentals |
| Sector EV/EBITDA median | Sector peer median | fundamentals |

### Signal Logic
**BUY** — all conditions:
1. P/E < 0.75 × sector median P/E
2. FCF yield > 5%
3. EV/EBITDA < sector median EV/EBITDA

**SELL** — any one:
1. P/E > 2.0 × sector median P/E
2. Negative FCF (FCF yield < 0%) for 2+ consecutive data points

**HOLD** — otherwise

### Confidence Score
```python
pe_discount   = max(0, (1 - pe_ratio / sector_pe_median)) * 40
fcf_score     = min(40, fcf_yield * 8)   # 5% yield → 40 pts
ev_discount   = max(0, (1 - ev_ebitda / sector_ev_ebitda_median)) * 20

confidence = min(100, pe_discount + fcf_score + ev_discount)
```

---

## Strategy 3: Dividend Growth (`dividend_growth`)

**Philosophy:** Compound income from companies with growing, sustainable dividends. Prioritize dividend safety and growth rate over yield alone.

**Timeframe:** Long-term (12+ months), income-oriented.

**Data requirements:** Dividend yield, payout ratio, 5-year dividend CAGR, consecutive years of dividend growth, earnings coverage ratio.

### Signal Logic
**BUY** — all conditions:
1. Dividend yield > 2.5%
2. Payout ratio < 60%
3. 5-year dividend CAGR > 5%
4. Consecutive years of dividend growth ≥ 5
5. Earnings coverage ratio > 2.0 (earnings / dividends per share)

**SELL** — any one:
1. Dividend cut announced or dividend yield drops > 30% (cut detected)
2. Payout ratio > 80% for 2 consecutive periods
3. Coverage ratio < 1.2 (dividend barely covered by earnings)

**HOLD** — otherwise

### Confidence Score
```python
# yield_score: 0-100, peaks at yield ~5%
yield_score = min(100, (dividend_yield / 5.0) * 100)

# sustainability_score: weighted combination of payout and coverage
payout_score    = max(0, (1 - payout_ratio / 60.0)) * 100  # 0%=100, 60%=0
coverage_score  = min(100, (coverage_ratio / 2.0) * 100)
sustainability_score = (payout_score * 0.5) + (coverage_score * 0.5)

# growth_score: CAGR and consecutive years
cagr_score        = min(100, (div_cagr_5y / 10.0) * 100)   # 10% CAGR = 100
years_score       = min(100, (consecutive_years / 10.0) * 100)
growth_score      = (cagr_score * 0.6) + (years_score * 0.4)

confidence = min(100, (yield_score * 0.25) + (sustainability_score * 0.40) + (growth_score * 0.35))
```

---

## Strategy 4: Mean Reversion (`mean_reversion`)

**Philosophy:** Buy quality stocks that have been oversold relative to recent history; sell when they revert to or exceed the mean.

**Timeframe:** Short-term, 1–4 weeks typical holding.

**Important:** This strategy is only applied to stocks that pass a basic quality filter (positive FCF, debt/equity < 2.0) to avoid catching falling knives.

**Data requirements:** 20+ days OHLCV, RSI, Bollinger Bands.

### Signal Logic
**BUY** — all conditions:
1. Price < lower Bollinger Band (20-day, 2σ)
2. RSI(14) < 35
3. Price > 10% below 50-day SMA

**Minimum confidence threshold for BUY: 60** (do not emit low-confidence mean reversion buys)

**SELL** — either:
1. Price > upper Bollinger Band AND RSI > 70
2. Price has recovered to 50-day SMA (take profit at mean)

**HOLD** — otherwise

### Confidence Score
```python
# How far below lower band
band_width     = upper_band - lower_band
band_deviation = max(0, (lower_band - close) / (band_width / 2)) * 40
band_deviation = min(40, band_deviation)

# RSI extremity (more oversold = higher score)
rsi_extremity  = max(0, (35 - rsi) / 35) * 40
rsi_extremity  = min(40, rsi_extremity)

# Distance from 50-day SMA
sma_distance   = max(0, (sma_50 - close) / sma_50) * 100 * 0.2
sma_distance   = min(20, sma_distance)

confidence = min(100, band_deviation + rsi_extremity + sma_distance)
```

---

## Strategy 5: Quality (`quality`)

**Philosophy:** Hold best-in-class businesses with durable competitive advantages. Trim or exit only when quality deteriorates — not on valuation or price.

**Timeframe:** Long-term, 3+ years.

**Data requirements:** ROE, ROIC, debt/equity, 5-year earnings consistency, gross margin history.

### Signal Logic
**BUY** — all conditions:
1. ROE > 15%
2. ROIC > 12%
3. Debt/equity < 0.5
4. Positive earnings in all 5 of the last 5 years
5. Gross margin trend flat or improving (no significant deterioration)

**SELL** — any one:
1. ROE < 10% for 2 consecutive annual periods
2. ROIC < 8% (approximate WACC threshold)
3. Debt/equity > 1.5

**HOLD** — default; price movements alone never trigger SELL in this strategy

### Confidence Score
```python
roe_score         = min(100, (roe / 15.0) * 100)
roic_score        = min(100, (roic / 12.0) * 100)
leverage_score    = min(100, max(0, (1 - debt_equity / 0.5)) * 100)
consistency_score = (positive_earnings_years / 5.0) * 100
margin_score      = 100 if margin_trend >= 0 else max(0, 100 + margin_trend * 500)

confidence = min(100,
    roe_score * 0.25 +
    roic_score * 0.25 +
    leverage_score * 0.20 +
    consistency_score * 0.15 +
    margin_score * 0.15
)
```

---

## Strategy 6: Growth (`growth`)

**Philosophy:** Invest in companies with durable, high revenue and earnings growth rates and expanding total addressable market. Ignore traditional value metrics; focus on growth trajectory.

**Timeframe:** Medium-to-long term, 1–5 years.

**Data requirements:** Revenue CAGR (3yr), EPS CAGR (3yr), gross margin, PEG ratio, revenue growth YoY (for acceleration/deceleration check).

### Signal Logic
**BUY** — all conditions:
1. Revenue CAGR (3yr) > 15%
2. EPS CAGR (3yr) > 15%
3. Gross margin > 40%
4. PEG ratio < 2.0
5. Revenue growth NOT decelerating by more than 20% YoY (avoids deteriorating growth stories)

**SELL** — any one:
1. Two consecutive quarters of revenue growth deceleration below 10%
2. Gross margin compression > 500 basis points YoY
3. PEG ratio > 4.0

**HOLD** — temporarily slowing growth with intact thesis (single quarter miss, macro headwind, one-time charge)

**Note:** High-growth stocks often trade at high P/E and may not pay dividends. This strategy deliberately ignores those traditional value signals.

### Confidence Score
```python
rev_growth_score  = min(100, (revenue_cagr_3y / 25.0) * 100)  # 25% CAGR = max
eps_growth_score  = min(100, (eps_cagr_3y / 25.0) * 100)
margin_score      = min(100, (gross_margin / 60.0) * 100)     # 60% margin = max
peg_score         = min(100, max(0, (1 - peg_ratio / 2.0)) * 100)  # PEG 0=100, PEG 2=0

confidence = min(100,
    rev_growth_score * 0.30 +
    eps_growth_score * 0.25 +
    margin_score * 0.20 +
    peg_score * 0.25
)
```

---

## Strategy 7: Long-Term Compounder (`long_term`)

**Philosophy:** Buy great businesses at fair prices and hold indefinitely. Let compounding do the work. The default action is HOLD. Price weakness is not a reason to sell — it may be a reason to add. Sell only on evidence of fundamental deterioration or moat erosion.

**Timeframe:** 5+ years. Extremely low portfolio turnover.

**Data requirements:** ROE (multi-year), FCF margin, revenue CAGR (5yr), P/FCF ratio, debt trend.

### Signal Logic
**BUY** — emitted for new watchlist adds or positions that meet all criteria:
1. ROE > 15% sustained over 5+ years (use 5yr average, not just last year)
2. FCF margin > 10%
3. Revenue CAGR (5yr) > 10%
4. Debt trend: stable or declining (debt/equity not increasing for 3+ years)
5. P/FCF < 40 (avoids grossly overvalued entries even for great businesses)

**SELL** — high bar; any of (sustained deterioration required, not a one-quarter blip):
1. ROE < 10% for 2+ consecutive annual periods
2. Free cash flow turns consistently negative (2+ quarters)
3. Debt/equity rises above 1.5 and is still rising
4. Clear evidence of moat erosion: sustained market share loss, pricing power decline, or major regulatory event

**HOLD** — default behavior for existing positions. Price decline alone never triggers SELL.

### Confidence Score
```python
roe_consistency   = min(100, (roe_5y_avg / 15.0) * 100)
fcf_margin_score  = min(100, (fcf_margin / 15.0) * 100)      # 15% FCF margin = max
growth_score      = min(100, (revenue_cagr_5y / 15.0) * 100) # 15% CAGR = max
valuation_score   = min(100, max(0, (1 - p_fcf / 40.0)) * 100)  # P/FCF 0=100, 40=0
debt_score        = 100 if debt_trend_stable else max(0, 100 - (debt_equity - 0.5) * 100)

confidence = min(100,
    roe_consistency * 0.30 +
    fcf_margin_score * 0.25 +
    growth_score * 0.20 +
    valuation_score * 0.15 +
    debt_score * 0.10
)
```

---

## Strategy 8: Hybrid / Combination Profiles (`hybrid:{name}`)

Users define hybrid profiles that blend multiple strategies with custom weights and a holding bias.

### HybridProfile Schema
```python
from pydantic import BaseModel

class StrategyWeight(BaseModel):
    strategy: str    # e.g. "growth", "long_term", "value"
    weight: float    # e.g. 0.6 — must sum to 1.0 across all weights

class HybridProfile(BaseModel):
    name: str                              # e.g. "Growth Long-Term"
    strategy_id: str                       # e.g. "growth_longterm" (used as DB key)
    components: list[StrategyWeight]
    holding_bias: Literal["short", "medium", "long"]
    description: str
```

### Holding Bias Effect
| Bias | Behavior |
|------|----------|
| `short` | All signals honored. Momentum and mean-reversion sell signals acted on quickly. |
| `medium` | Standard signal logic. All strategy signals contribute normally. |
| `long` | Technical sell signals (momentum, mean reversion) are suppressed for existing positions. Only fundamental deterioration (value, quality, long_term) triggers SELL. |

### Hybrid Confidence Calculation
```python
# Weighted average of component strategy confidences
component_confidences = {
    strategy: signal.confidence
    for strategy, signal in component_signals.items()
}
hybrid_confidence = sum(
    component_confidences[s.strategy] * s.weight
    for s in profile.components
    if s.strategy in component_confidences
)

# Holding bias adjustment for SELL signals
if signal == "SELL" and profile.holding_bias == "long":
    if triggering_strategy in ["momentum", "mean_reversion"]:
        signal = "HOLD"
        hybrid_confidence = 0
```

### Preset Hybrid Profiles
| Name | Components | Holding Bias | Description |
|------|-----------|--------------|-------------|
| Growth Long-Term | 60% Growth + 40% Long-Term | long | Buy growth compounders; hold through corrections; sell only on fundamental deterioration |
| Income & Value | 50% Dividend Growth + 50% Value | medium | Undervalued dividend payers |
| Balanced | 33% Momentum + 33% Value + 34% Quality | medium | Generalist blend |
| Aggressive Growth | 70% Growth + 30% Momentum | short | High-growth momentum plays; quicker to exit |
| Defensive Quality | 60% Quality + 40% Dividend Growth | long | Capital preservation with income |

---

## Smart Recommendation Engine (AI Synthesis Layer)

Raw strategy signals are inputs to a higher-level AI layer powered by Claude (`claude-sonnet-4-5`). This engine runs after all strategies and hybrid profiles have been computed.

### What the Engine Synthesizes
1. All strategy signals + confidence scores for the symbol
2. Portfolio context: current position weight (% of portfolio), sector allocation, available cash
3. User preferences: investment horizon, risk tolerance, max single position %, preferred strategies, tax sensitivity, min confidence threshold
4. Market conditions: broad market trend (S&P 500 50-day vs 200-day SMA), VIX proxy (market volatility estimate)
5. Position metadata: cost basis, holding period, unrealized gain/loss (for tax-aware decisions)

### SmartRecommendation Output
```python
@dataclass
class SmartRecommendation:
    symbol: str
    action: Literal["BUY", "ADD", "TRIM", "SELL", "HOLD", "WATCH"]
    urgency: Literal["high", "medium", "low"]
    suggested_size_pct: float      # % of total portfolio
    suggested_tranche: int         # current tranche (e.g. 1)
    total_tranches: int            # total tranches in plan (e.g. 3)
    timing_note: str               # e.g. "Earnings in 8 days — consider waiting"
    rationale: str                 # Claude-generated full reasoning (2-4 paragraphs)
    conflicting_signals: list[str] # strategies that disagree with the action
    supporting_strategies: list[str]
    risk_factors: list[str]
    model_used: str
    generated_at: datetime
    expires_at: datetime
```

### Action Definitions
| Action | Meaning |
|--------|---------|
| BUY | Initiate a new position (not currently held) |
| ADD | Add to an existing position (scale in) |
| TRIM | Partially reduce existing position (scale out) |
| SELL | Exit entire position |
| HOLD | No action; maintain current position |
| WATCH | On watchlist, not yet actionable — monitor for entry conditions |

### Scale-In / Scale-Out Logic
The engine does not recommend all-in or all-out by default. When buying:
- If user has `scale_in_enabled = True`, a BUY is split into N tranches (default 3)
- Tranche 1: initial position (~1/3 of target size)
- Subsequent tranches triggered by new recommendation refreshes as conviction builds
- Tranche plan is stored and resumed on future refreshes

When selling or trimming:
- TRIM suggests reducing by 1/3 of position, not full exit
- SELL is reserved for high-conviction exits (strategy deterioration, user's max loss threshold)
- If tax_sensitive = True: SELL/TRIM notes short-term vs long-term gain status

### Claude Prompt Structure
```
System: You are a senior portfolio analyst assistant. You reason carefully about
investment decisions, considering both quantitative signals and qualitative context.
You never recommend all-in or all-out trades unless conviction is extremely high.
You always explain your reasoning in plain language.

User:
[SYMBOL]: {symbol} | Current position: {position_pct:.1f}% of portfolio
Current price: ${current_price} | Avg cost: ${avg_cost} | P&L: {unrealized_pnl_pct:.1f}%
Holding period: {holding_days} days

STRATEGY SIGNALS:
{formatted_signals_table}

PORTFOLIO CONTEXT:
- Total portfolio value: ${portfolio_value:,.0f}
- Available cash: ${available_cash:,.0f}
- Sector ({sector}) allocation: {sector_pct:.1f}% (max: {max_sector_pct:.1f}%)
- Broad market trend: {market_trend}

USER PREFERENCES:
- Investment horizon: {horizon}
- Risk tolerance: {risk_tolerance}
- Max single position: {max_position_pct:.1f}%
- Tax sensitive: {tax_sensitive}
- Min confidence to act: {min_confidence}
- Preferred strategies: {preferred_strategies}

Generate a SmartRecommendation in JSON format...
```
