import yfinance as yf
import pandas as pd
import numpy as np

PEERS = {
    "GOOGL": "Google",
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "META": "Meta",
    "AMZN": "Amazon",
    "NVDA": "Nvidia",
}
BENCHMARKS = {"SPY": "S&P 500", "XLK": "Tech Sector"}
MACRO_TICKERS = {"^TNX": "10Y Treasury", "^VIX": "VIX", "DX-Y.NYB": "US Dollar"}


def get_peer_comparison(ticker: str, period: str = "6mo") -> dict:
    peers = {k: v for k, v in PEERS.items() if k != ticker}
    all_tickers = [ticker] + list(peers.keys()) + list(BENCHMARKS.keys())

    data = yf.download(all_tickers, period=period, interval="1d", progress=False)
    if data.empty:
        return {"available": False}

    close = data["Close"] if "Close" in data.columns else data.get("close", pd.DataFrame())
    if close.empty:
        return {"available": False}

    returns = close.pct_change(fill_method=None)
    cum_returns = (1 + returns).cumprod() - 1

    corr = returns.corr()
    ticker_corr = corr[ticker].drop(ticker, errors="ignore").sort_values(ascending=False)

    latest_cum = cum_returns.iloc[-1]

    # Relative strength vs SPY
    if "SPY" in cum_returns.columns and ticker in cum_returns.columns:
        rel_strength = cum_returns[ticker] - cum_returns["SPY"]
    else:
        rel_strength = pd.Series(dtype=float)

    return {
        "available": True,
        "cumulative_returns": cum_returns,
        "correlation": ticker_corr.to_dict(),
        "period_returns": latest_cum.to_dict(),
        "relative_strength_vs_spy": rel_strength,
        "names": {**PEERS, **BENCHMARKS},
    }


def get_macro_indicators(period: str = "1y") -> dict:
    data = yf.download(list(MACRO_TICKERS.keys()), period=period, interval="1d", progress=False)
    if data.empty:
        return {"available": False}

    close = data["Close"] if "Close" in data.columns else data.get("close", pd.DataFrame())
    if close.empty:
        return {"available": False}

    close = close.rename(columns=MACRO_TICKERS)
    return {
        "available": True,
        "data": close,
        "names": MACRO_TICKERS,
    }


def get_analyst_data(ticker: str) -> dict:
    stock = yf.Ticker(ticker)

    # Price targets
    try:
        targets = stock.analyst_price_targets
    except Exception:
        targets = None

    # Recommendations
    try:
        recs = stock.recommendations
        if recs is not None and not recs.empty:
            recs = recs.head(4)
    except Exception:
        recs = None

    # EPS estimates
    try:
        eps_est = stock.earnings_estimate
    except Exception:
        eps_est = None

    # Revenue estimates
    try:
        rev_est = stock.revenue_estimate
    except Exception:
        rev_est = None

    return {
        "price_targets": targets,
        "recommendations": recs,
        "eps_estimate": eps_est,
        "revenue_estimate": rev_est,
    }


def get_earnings_impact(ticker: str, price_df: pd.DataFrame) -> pd.DataFrame:
    stock = yf.Ticker(ticker)
    try:
        earnings = stock.earnings_dates
    except Exception:
        return pd.DataFrame()

    if earnings is None or earnings.empty:
        return pd.DataFrame()

    rows = []
    for date in earnings.index:
        date_naive = date.tz_localize(None) if hasattr(date, "tz_localize") and date.tzinfo else date
        date_only = pd.Timestamp(date_naive.date())

        idx = price_df.index.get_indexer([date_only], method="nearest")
        if idx[0] < 0 or idx[0] >= len(price_df):
            continue

        pos = idx[0]
        if pos < 1 or pos >= len(price_df) - 1:
            continue

        close_before = price_df["close"].iloc[pos - 1]
        close_on = price_df["close"].iloc[pos]
        close_after = price_df["close"].iloc[min(pos + 1, len(price_df) - 1)]

        day_return = (close_on - close_before) / close_before * 100
        next_day_return = (close_after - close_on) / close_on * 100

        eps_est = earnings.loc[date].get("EPS Estimate")
        eps_actual = earnings.loc[date].get("Reported EPS")
        surprise = None
        if pd.notna(eps_est) and pd.notna(eps_actual) and eps_est != 0:
            surprise = (eps_actual - eps_est) / abs(eps_est) * 100

        rows.append({
            "date": date_only.strftime("%Y-%m-%d"),
            "eps_estimate": eps_est if pd.notna(eps_est) else None,
            "eps_actual": eps_actual if pd.notna(eps_actual) else None,
            "surprise_pct": round(surprise, 2) if surprise is not None else None,
            "day_return_pct": round(day_return, 2),
            "next_day_return_pct": round(next_day_return, 2),
        })

    return pd.DataFrame(rows)
