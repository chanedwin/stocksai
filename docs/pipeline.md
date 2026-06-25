# Stock Analysis Pipeline

## Overview

The pipeline fetches stock market data, computes technical and fundamental analysis, and serves it through an interactive Streamlit dashboard. It defaults to Google (GOOGL) but supports any publicly traded ticker.

## Architecture

```
pipeline/
  data_fetcher.py           Pulls price (OHLCV) and fundamental data via yfinance
  technical_analysis.py     Computes TA indicators on a price DataFrame
  fundamental_analysis.py   Extracts ratios and cleans financial statements

dashboard/
  app.py                    Streamlit app that ties the pipeline together

data/                       Cached/exported data (gitignored contents)
```

## Data Sources

All data comes from **yfinance**, which pulls from Yahoo Finance. No API key required.

- **Price data**: OHLCV at daily resolution, configurable period (6mo to max)
- **Fundamental data**: income statement, balance sheet, cash flow (annual + quarterly), plus company info and earnings dates

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

## Running the Dashboard

```bash
pip install -r requirements.txt
streamlit run dashboard/app.py
```

The dashboard runs on `http://localhost:8501` by default.

## Dashboard Features

- Candlestick chart with configurable overlays (moving averages, Bollinger Bands)
- RSI subplot with overbought/oversold markers (70/30)
- MACD subplot with signal line and histogram
- Volume bars colored by price direction, with 20-day SMA
- Key metric cards (price, change, market cap, P/E, EPS, dividend yield)
- Fundamental ratio breakdowns by category
- Full financial statements (annual + quarterly) in tabbed views
- Earnings history table
- Company description
