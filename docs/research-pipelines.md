# Research Pipelines

> **Keep this document current.** When you add, remove, or change a pipeline module or its functions, update the relevant section here in the same commit. Each section is self-contained so agents can read only what they need.
> Project state and next steps: `docs/status.md`. Approved build plans: `docs/plans/`.

---

<!-- SECTION: data-fetcher -->
## 1. Data Fetcher

**Module:** `pipeline/data_fetcher.py`
**Source:** yfinance (Yahoo Finance). No API key required.

| Function | Input | Output | Notes |
|----------|-------|--------|-------|
| `fetch_price_data(ticker, period, interval)` | ticker str, period (default "2y"), interval (default "1d") | DataFrame with columns: open, high, low, close, volume. Index is tz-naive DatetimeIndex. | Returns empty DataFrame on invalid ticker. Lowercases column names. |
| `fetch_fundamental_data(ticker)` | ticker str | dict with keys: info, income_stmt, quarterly_income_stmt, balance_sheet, quarterly_balance_sheet, cashflow, quarterly_cashflow, earnings_dates | earnings_dates may be empty if unavailable. |

**Gotchas:**
- yfinance returns tz-aware indexes for some tickers. `fetch_price_data` strips timezone to keep everything naive/UTC.
- Empty DataFrame guard: returns early if download yields no rows.

---

<!-- SECTION: technical-analysis -->
## 2. Technical Analysis

**Module:** `pipeline/technical_analysis.py`
**Dependency:** `ta` library (not pandas_ta, which requires Python <3.14).

| Function | Input | Output |
|----------|-------|--------|
| `compute_indicators(df)` | OHLCV DataFrame | Same DataFrame with indicator columns appended |

**Indicators added:**

| Category | Column(s) | Parameters |
|----------|-----------|------------|
| Trend | sma_20, sma_50, sma_200 | Simple moving averages |
| Trend | ema_12, ema_26 | Exponential moving averages |
| Momentum | rsi | RSI(14) |
| Momentum | MACD_12_26_9, MACDs_12_26_9, MACDh_12_26_9 | MACD line, signal, histogram |
| Momentum | stoch_k, stoch_d | Stochastic(14,3,3) |
| Volatility | BBU_20_2.0, BBM_20_2.0, BBL_20_2.0 | Bollinger Bands(20,2) |
| Volatility | atr | ATR(14) |
| Volume | obv | On-balance volume |
| Volume | volume_sma_20 | 20-day volume average |
| Volume | vwap | 20-day rolling VWAP (not cumulative) |
| Returns | daily_return, cumulative_return | Percentage returns |

---

<!-- SECTION: fundamental-analysis -->
## 3. Fundamental Analysis

**Module:** `pipeline/fundamental_analysis.py`

| Function | Input | Output |
|----------|-------|--------|
| `compute_ratios(info)` | yfinance info dict | Nested dict by category: Valuation, Profitability, Growth, Financial Health, Cash Flow, Dividends |
| `get_financial_statements(fundamentals)` | fundamentals dict from data_fetcher | dict of cleaned DataFrames: annual/quarterly income, balance, cashflow |

**Ratio categories:**
- **Valuation:** P/E trailing + forward, PEG, P/B, P/S, EV/EBITDA, EV/Revenue
- **Profitability:** Gross/operating/net margin, ROE, ROA
- **Growth:** Revenue growth YoY, earnings growth YoY, EPS trailing + forward
- **Financial Health:** Debt/equity, current ratio, quick ratio
- **Cash Flow:** Operating cash flow, free cash flow
- **Dividends:** Yield, payout ratio

---

<!-- SECTION: flow-analysis -->
## 4. Flow Analysis

**Module:** `pipeline/flow_analysis.py`

| Function | Input | Output | Notes |
|----------|-------|--------|-------|
| `get_ownership_breakdown(info)` | info dict | dict: insiders_pct, institutions_pct, institutions_count, float_shares, shares_outstanding | |
| `get_institutional_holders(ticker)` | ticker str | DataFrame of top holders with shares, value, pctHeld, pctChange | |
| `get_mutualfund_holders(ticker)` | ticker str | DataFrame of top mutual fund holders | |
| `get_insider_activity(ticker)` | ticker str | dict: transactions (DataFrame), summary (DataFrame, 6-month buys/sells) | Transaction type is in the Text column, not the Transaction column. |
| `get_short_interest(info)` | info dict | dict: shares_short, shares_short_prior_month, short_change_pct, short_pct_of_float, short_ratio | |
| `get_options_flow(ticker, max_expirations)` | ticker str, max 4 expirations | dict: call/put volume+OI, P/C ratios, max_pain, unusual_activity list | Unusual = volume > 3x open interest |

**Max pain calculation:** Iterates all strikes to find the price where total option holder losses are minimized. Uses OI-weighted pain for both calls and puts.

---

<!-- SECTION: pattern-detection -->
## 5. Pattern Detection

**Module:** `pipeline/pattern_detection.py`

| Function | Input | Output |
|----------|-------|--------|
| `detect_support_resistance(df, window=20, num_levels=5)` | OHLCV DataFrame | dict: support list, resistance list, current_price. Each level has price, touches, first_seen, last_seen. |
| `detect_signals(df)` | DataFrame with indicators | list of signal dicts: signal, type (bullish/bearish/neutral), strength (strong/moderate/weak), description |
| `compute_trend_scores(df, info)` | indicator DataFrame + info dict | dict with trend, momentum, volatility, short_interest scores |

**Signals detected:**
- Golden Cross / Death Cross (SMA 50 vs 200)
- RSI overbought (>70), oversold (<30), midline cross
- MACD bullish/bearish crossover
- Bollinger Band break (above upper / below lower), squeeze (bandwidth <0.04)
- Volume spike (>2x 20-day average)
- Price position vs SMA 200 and SMA 50

**S/R detection:** Requires 40+ trading days (2x window). Uses 2% tolerance clustering. Levels sorted by touch count.

---

<!-- SECTION: market-context -->
## 6. Market Context

**Module:** `pipeline/market_context.py`

| Function | Input | Output |
|----------|-------|--------|
| `get_peer_comparison(ticker, period)` | ticker str, period str | dict: cumulative_returns DataFrame, correlation dict, period_returns dict, relative_strength_vs_spy Series |
| `get_macro_indicators(period)` | period str | dict: data DataFrame with 10Y Treasury, VIX, US Dollar columns |
| `get_analyst_data(ticker)` | ticker str | dict: price_targets, recommendations, eps_estimate, revenue_estimate |
| `get_earnings_impact(ticker, price_df)` | ticker str, OHLCV DataFrame | DataFrame: date, eps_estimate, eps_actual, surprise_pct, day_return_pct, next_day_return_pct |

**Peer group:** GOOGL, AAPL, MSFT, META, AMZN, NVDA (Mag7 minus the queried ticker).
**Benchmarks:** SPY (S&P 500), XLK (Tech Sector).
**Macro tickers:** ^TNX (10Y Treasury yield), ^VIX (fear index), DX-Y.NYB (US Dollar index).

---

<!-- SECTION: earnings-analysis -->
## 7. Earnings Analysis

**Module:** `pipeline/earnings_analysis.py`

| Function | Input | Output |
|----------|-------|--------|
| `compute_growth_trends(fundamentals)` | fundamentals dict | dict: quarterly + annual, each with rows list (metric, latest, previous, yoy_growth, seq_growth) and periods |
| `compute_margin_trends(fundamentals)` | fundamentals dict | dict: quarterly + annual, each with margins dict (Gross/Operating/Net Margin, R&D % Revenue) and periods |
| `compute_revenue_composition(fundamentals)` | fundamentals dict | dict: available bool, period, total_revenue, components (each with value and pct_of_revenue) |

**Key P&L metrics tracked:** Total Revenue, Cost of Revenue, Gross Profit, Operating Expenses, Operating Income, Net Income, R&D, Diluted EPS.

**YoY for quarterly:** Compares to the quarter 4 periods back (same quarter prior year), not the immediately preceding quarter.

**Limitation:** yfinance provides only aggregate revenue. Segment-level breakdown (e.g., Google Search vs Cloud vs YouTube) requires SEC EDGAR 10-K/10-Q filings, which are not yet integrated.

---

<!-- SECTION: signal-aggregator -->
## 8. Signal Aggregator

**Module:** `pipeline/signal_aggregator.py`

| Function | Input | Output |
|----------|-------|--------|
| `aggregate_all_signals(price_df, info, fundamentals, ticker)` | 5-year OHLCV, info dict, fundamentals dict, ticker str | dict: composite_score (-100 to +100), verdict, category_scores, timeframe_scores, all_signals list, yearly_performance, seasonal |
| `compute_timeframe_signals(price_df)` | OHLCV DataFrame | dict keyed by daily/weekly/monthly, each with signals list and df |
| `compute_seasonal_analysis(price_df)` | OHLCV DataFrame (needs 252+ days) | dict: monthly (avg return, win rate per month), day_of_week, quarterly |
| `compute_yearly_performance(price_df)` | OHLCV DataFrame | list of dicts: year, return_pct, high, low, range_pct |
| `compute_flow_signals(info, ticker)` | info dict, ticker str | list of flow signal dicts |
| `compute_fundamental_signals(info, fundamentals)` | info dict, fundamentals dict | list of fundamental signal dicts |
| `compute_analyst_signals(ticker)` | ticker str | list of analyst signal dicts |
| `compute_sr_signals(sr_levels)` | S/R levels dict | list of proximity signal dicts |

**Signal schema:** Each signal is a dict with keys: signal (name), type (bullish/bearish/neutral), strength (strong/moderate/weak), category (technical/fundamental/flow/analyst), timeframe (daily/weekly/monthly/current), description.

**Composite scoring:** Weights: strong=3, moderate=2, weak=1. Score = (bullish_weight - bearish_weight) / total_weight * 100. Verdict thresholds: >40 Bullish, >15 Slightly Bullish, >-15 Neutral, >-40 Slightly Bearish, else Bearish.

**Timeframe resampling:** Daily data is resampled to weekly (W) and monthly (ME) OHLCV, then indicators and signals are computed independently on each.

**Seasonal analysis:** Requires at least 1 year (252 trading days). Computes per-month and per-quarter average returns and win rates across all available years. Day-of-week analysis covers Mon-Fri.

---

<!-- SECTION: congress-trades -->
## 9. Congressional Trades

**Module:** `pipeline/congress_trades.py`
**Source:** kadoa-org/congress-trading-monitor GitHub dataset (static JSON files from parsed STOCK Act disclosures). No API key required.

| Function | Input | Output | Notes |
|----------|-------|--------|-------|
| `get_filers()` | none | DataFrame of 432 politicians with trade_count, party, chamber, state, office | Sorted by trade_count descending. Cached in memory. |
| `get_trades_for_ticker(ticker)` | ticker str | DataFrame of all congressional trades in that stock | Columns: transaction_date, filer_name, party, transaction_type, amount_range_label, ret_since, etc. |
| `get_trades_for_filer(filer_id)` | filer_id str (e.g. "house_nancy_pelosi") | dict with "filer" (metadata) and "trades" (DataFrame) | Returns empty trades DataFrame if filer not found. |
| `get_ticker_summary(ticker)` | ticker str | dict with trade_count, filer_count, purchases, sales, est_volume | Empty dict if ticker has no congressional trades. |
| `compute_trade_stats(trades_df)` | DataFrame from get_trades_for_ticker | dict with total, purchases, sales, unique_filers, by_party, by_chamber | Used by dashboard for summary cards and party breakdown. |
| `estimate_volume(row)` | single trade row (dict-like) | float estimated dollar amount | Midpoint of amount_range_low and amount_range_high. |
| `get_top_traders(limit)` | int (default 20) | DataFrame of top N politicians by trade count | Convenience wrapper over get_filers(). |

**Data fields per trade:** id, source_id, transaction_date, filing_date, owner (self/SP/JT/DC), ticker, asset_name, asset_type (ST/OP), transaction_type (Purchase/Sale/Sale (Full)/Sale (Partial)/Exchange), amount_range_low, amount_range_high, amount_range_label, days_to_file, is_late, comment, filer_name, party, chamber, state, ret_since, excess_since, doc_url.

**Gotchas:**
- Data is from a third-party GitHub repo that parses official STOCK Act filings. Updates depend on that project's ingestion schedule.
- The `_cache` dict uses a 60-minute TTL. Streamlit also caches at 3600s (1 hour) for congress data.
- Owner codes: SP=Spouse, JT=Joint, DC=Dependent Child, null=Self.
- Asset type: ST=Stock, OP=Options.

---

<!-- SECTION: dashboard -->
## 10. Dashboard

**Module:** `dashboard/app.py`
**Framework:** Streamlit + Plotly

**Sections (top to bottom):**
1. Header: company name, sector, key metrics (price, change, market cap, P/E, EPS, div yield)
2. Signal Overview: composite gauge, category breakdown bars, timeframe cards, signal tabs, yearly performance, seasonal charts, disclaimer
3. Technical Analysis: candlestick with overlays, RSI, MACD, volume subplots, S/R tables, indicator cards
4. Money Flow: ownership pie, insider summary, short interest, options flow, institutional holders, insider transactions (color-coded Sale/Purchase/Gift)
5. Market Context (toggle): analyst consensus, peer comparison, macro indicators, earnings impact
6. Earnings Breakdown: revenue composition waterfall, quarterly growth cards, margin trends
7. Congressional Trading Activity (toggle): summary metrics, buy/sell bar, party breakdown, timeline scatter, recent trades table, politician lookup with per-filer trade history
8. Fundamental Analysis: ratio cards by category
9. Financial Statements: tabbed annual/quarterly views
10. Earnings History table
11. Company description

**Caching:** `@st.cache_data(ttl=900)` on data loaders. Signal analysis always uses 5-year data regardless of period selector.

**Color system:** GREEN=#26a69a, RED=#ef5350, YELLOW=#ffa726, BLUE=#42a5f5, GREY=#9e9e9e. For Plotly transparency, use `rgba()` format (Plotly rejects 8-digit hex).
