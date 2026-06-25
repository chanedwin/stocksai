import requests
import pandas as pd
from datetime import datetime

BASE_URL = "https://raw.githubusercontent.com/kadoa-org/congress-trading-monitor/main/public/data"
_cache = {}


def _fetch_json(path, ttl_minutes=60):
    now = datetime.utcnow().timestamp()
    if path in _cache:
        data, fetched_at = _cache[path]
        if now - fetched_at < ttl_minutes * 60:
            return data
    url = f"{BASE_URL}/{path}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    data = r.json()
    _cache[path] = (data, now)
    return data


def get_filers():
    raw = _fetch_json("filers.json")
    df = pd.DataFrame(raw)
    df = df.sort_values("trade_count", ascending=False)
    return df


def get_trades_for_ticker(ticker: str) -> pd.DataFrame:
    try:
        data = _fetch_json(f"ticker/{ticker.upper()}.json")
    except (requests.HTTPError, requests.ConnectionError, requests.Timeout):
        return pd.DataFrame()
    trades = data.get("trades", [])
    if not trades:
        return pd.DataFrame()
    df = pd.DataFrame(trades)
    df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    df = df.sort_values("transaction_date", ascending=False)
    return df


def get_trades_for_filer(filer_id: str) -> dict:
    try:
        data = _fetch_json(f"filer/{filer_id}.json")
    except (requests.HTTPError, requests.ConnectionError, requests.Timeout):
        return {"filer": {}, "trades": []}
    filer = data.get("filer", {})
    trades = data.get("trades", [])
    if trades:
        df = pd.DataFrame(trades)
        df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
        df = df.sort_values("transaction_date", ascending=False)
    else:
        df = pd.DataFrame()
    return {"filer": filer, "trades": df}


def get_ticker_summary(ticker: str) -> dict:
    try:
        tickers = _fetch_json("tickers.json")
    except (requests.HTTPError, requests.ConnectionError, requests.Timeout):
        return {}
    match = [t for t in tickers if t.get("ticker") == ticker.upper()]
    return match[0] if match else {}


def compute_trade_stats(trades_df: pd.DataFrame) -> dict:
    if trades_df.empty:
        return {
            "total": 0,
            "purchases": 0,
            "sales": 0,
            "unique_filers": 0,
            "latest_date": None,
            "by_party": {},
            "by_chamber": {},
        }

    purchases = trades_df["transaction_type"].str.contains("Purchase", case=False, na=False).sum()
    sales = trades_df["transaction_type"].str.contains("Sale", case=False, na=False).sum()

    by_party = {}
    if "party" in trades_df.columns:
        for party, group in trades_df.groupby("party"):
            if pd.isna(party):
                continue
            p = group["transaction_type"].str.contains("Purchase", case=False, na=False).sum()
            s = group["transaction_type"].str.contains("Sale", case=False, na=False).sum()
            by_party[party] = {"purchases": int(p), "sales": int(s), "total": len(group)}

    by_chamber = {}
    if "chamber" in trades_df.columns:
        for chamber, group in trades_df.groupby("chamber"):
            if pd.isna(chamber):
                continue
            by_chamber[chamber] = len(group)

    filer_col = "filer_name" if "filer_name" in trades_df.columns else "filer_id"
    latest = trades_df["transaction_date"].max()

    return {
        "total": len(trades_df),
        "purchases": int(purchases),
        "sales": int(sales),
        "unique_filers": trades_df[filer_col].nunique() if filer_col in trades_df.columns else 0,
        "latest_date": latest.strftime("%Y-%m-%d") if pd.notna(latest) else None,
        "by_party": by_party,
        "by_chamber": by_chamber,
    }


def estimate_volume(row):
    low = row.get("amount_range_low", 0) or 0
    high = row.get("amount_range_high", 0) or 0
    if low and high:
        return (low + high) / 2
    return low or high or 0
