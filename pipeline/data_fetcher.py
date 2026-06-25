import yfinance as yf
import pandas as pd


def fetch_price_data(ticker: str, period: str = "2y", interval: str = "1d") -> pd.DataFrame:
    stock = yf.Ticker(ticker)
    df = stock.history(period=period, interval=interval)
    if df.empty:
        return df
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    df = df.rename(columns={
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume",
    })
    df = df[["open", "high", "low", "close", "volume"]]
    return df


def fetch_fundamental_data(ticker: str) -> dict:
    stock = yf.Ticker(ticker)
    info = stock.info or {}

    return {
        "info": info,
        "income_stmt": stock.income_stmt,
        "quarterly_income_stmt": stock.quarterly_income_stmt,
        "balance_sheet": stock.balance_sheet,
        "quarterly_balance_sheet": stock.quarterly_balance_sheet,
        "cashflow": stock.cashflow,
        "quarterly_cashflow": stock.quarterly_cashflow,
        "earnings_dates": _safe_earnings_dates(stock),
    }


def _safe_earnings_dates(stock) -> pd.DataFrame:
    try:
        return stock.earnings_dates
    except Exception:
        return pd.DataFrame()
