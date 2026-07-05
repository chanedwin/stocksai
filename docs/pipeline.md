# Stock Analysis Pipeline

## Overview

The pipeline fetches stock market data, computes technical and fundamental analysis, detects patterns and money flow signals, and serves it through an interactive Streamlit dashboard. It defaults to Google (GOOGL) but supports any publicly traded ticker.

## Architecture

```
pipeline/
  data_fetcher.py           Pulls price (OHLCV) and fundamental data via yfinance
  technical_analysis.py     Computes TA indicators on a price DataFrame
  fundamental_analysis.py   Extracts ratios and cleans financial statements
  flow_analysis.py          Institutional ownership, insider activity, short interest, options flow
  pattern_detection.py      Support/resistance, trading signals, trend scores
  market_context.py         Peer comparison, macro indicators, analyst data, earnings impact
  earnings_analysis.py      Revenue/earnings growth trends, margin analysis, P&L composition
  signal_aggregator.py      Composite score from all signal categories, timeframes, seasonality
  congress_trades.py        Congressional stock trade data from STOCK Act disclosures

dashboard/
  app.py                    Streamlit app that ties the pipeline together

data/                       Cached/exported data (gitignored contents)
```

## Data Sources

Most data comes from **yfinance**, which pulls from Yahoo Finance. No API key required.

- **Price data**: OHLCV at daily resolution, configurable period (6mo to max)
- **Fundamental data**: income statement, balance sheet, cash flow (annual + quarterly), plus company info and earnings dates
- **Macro data**: 10Y Treasury yield, VIX, and US Dollar index via yfinance index tickers
- **Congressional trades**: kadoa-org/congress-trading-monitor GitHub dataset (parsed STOCK Act disclosures), no API key required

## Technical Analysis Indicators

| Category   | Indicator              | Parameters       |
|------------|------------------------|------------------|
| Trend      | SMA                    | 20, 50, 200 day |
| Trend      | EMA                    | 12, 26 day      |
| Momentum   | RSI                    | 14 period        |
| Momentum   | MACD                   | 12, 26, 9        |
| Momentum   | Stochastic Oscillator  | 14, 3, 3         |
| Volatility | Bollinger Bands        | 20 period, 2 std |
| Volatility | ATR                    | 14 period        |
| Volume     | OBV                    | -                |
| Volume     | Volume SMA             | 20 day           |
| Volume     | VWAP                   | daily approx     |
| Returns    | Daily return           | 1 day            |
| Returns    | Cumulative return      | from start       |

## Fundamental Analysis Metrics

**Valuation**: P/E (trailing + forward), PEG, P/B, P/S, EV/EBITDA, EV/Revenue

**Profitability**: Gross margin, operating margin, net margin, ROE, ROA

**Growth**: Revenue growth YoY, earnings growth YoY, EPS (trailing + forward)

**Financial Health**: Debt/equity, current ratio, quick ratio

**Cash Flow**: Operating cash flow, free cash flow

**Dividends**: Dividend yield, payout ratio

## Money Flow Analysis

- **Ownership breakdown**: % held by insiders, institutions, retail (from yfinance info)
- **Institutional holders**: top holders with shares, value, and position changes
- **Insider activity**: recent transactions (buys/sells) and 6-month summary
- **Short interest**: shares short, % of float, days to cover, month-over-month change
- **Options flow**: put/call ratio (volume and OI), max pain strike, unusual activity (volume > 3x OI)

## Pattern Detection

**Support/Resistance**: local minima/maxima detection with 2% tolerance clustering. Levels show touch count and distance from current price. Requires at least 40 trading days of data.

**Trading Signals**:
- Golden Cross / Death Cross (SMA 50 vs 200)
- RSI overbought (>70) / oversold (<30) / midline cross
- MACD bullish/bearish crossover
- Bollinger Band break / squeeze
- Volume spikes (>2x 20-day average)
- Price vs SMA position

**Trend Scores**: composite scores for trend (MA alignment), momentum (RSI + MACD), volatility (ATR%), and short interest sentiment.

## Running the Dashboard

```bash
pip install -r requirements.txt
streamlit run dashboard/app.py
```

The dashboard runs on `http://localhost:8501` by default.

## Dashboard Features

- Signal Overview: composite score gauge, category and timeframe breakdowns, yearly performance, seasonal charts
- Market Context (toggle): analyst consensus, peer comparison, macro indicators, earnings impact
- Earnings Breakdown: revenue composition, quarterly growth cards, margin trends
- Congressional Trading Activity (toggle): summary metrics, party breakdown, timeline, politician lookup
- Trend scores and active signal badges (color-coded bullish/bearish/neutral)
- Candlestick chart with configurable overlays (MAs, Bollinger Bands, support/resistance lines)
- RSI subplot with shaded overbought/oversold zones
- MACD subplot with signal line and color-coded histogram
- Volume bars colored by price direction, with 20-day SMA
- Color-coded indicator cards (price vs MA, RSI status, MACD direction, ATR volatility)
- Support/resistance tables with touch count and distance from price
- Money Flow section: ownership pie chart, insider activity summary, short interest with MoM trend
- Options flow: put/call ratios, max pain, unusual activity table
- Institutional holders and insider transaction tables
- Fundamental ratio cards with color-coded values
- Full financial statements (annual + quarterly) in tabbed views
- Earnings history table
- Company description
