import yfinance as yf
import pandas as pd


def get_ownership_breakdown(info: dict) -> dict:
    return {
        "insiders_pct": info.get("heldPercentInsiders"),
        "institutions_pct": info.get("heldPercentInstitutions"),
        "institutions_count": info.get("institutionsCount"),
        "float_shares": info.get("floatShares"),
        "shares_outstanding": info.get("sharesOutstanding"),
    }


def get_institutional_holders(ticker: str) -> pd.DataFrame:
    stock = yf.Ticker(ticker)
    df = stock.institutional_holders
    if df is None or df.empty:
        return pd.DataFrame()
    return df


def get_mutualfund_holders(ticker: str) -> pd.DataFrame:
    stock = yf.Ticker(ticker)
    df = stock.mutualfund_holders
    if df is None or df.empty:
        return pd.DataFrame()
    return df


def get_insider_activity(ticker: str) -> dict:
    stock = yf.Ticker(ticker)
    transactions = stock.insider_transactions
    if transactions is None:
        transactions = pd.DataFrame()

    purchases = stock.insider_purchases
    if purchases is None:
        purchases = pd.DataFrame()

    return {
        "transactions": transactions,
        "summary": purchases,
    }


def get_short_interest(info: dict) -> dict:
    shares_short = info.get("sharesShort")
    shares_short_prior = info.get("sharesShortPriorMonth")
    short_change = None
    if shares_short is not None and shares_short_prior is not None and shares_short_prior > 0:
        short_change = (shares_short - shares_short_prior) / shares_short_prior

    return {
        "shares_short": shares_short,
        "shares_short_prior_month": shares_short_prior,
        "short_change_pct": short_change,
        "short_pct_of_float": info.get("shortPercentOfFloat"),
        "short_ratio": info.get("shortRatio"),
    }


def get_options_flow(ticker: str, max_expirations: int = 4) -> dict:
    stock = yf.Ticker(ticker)
    expirations = stock.options
    if not expirations:
        return {"available": False}

    expirations = expirations[:max_expirations]
    all_calls = []
    all_puts = []

    for exp in expirations:
        try:
            chain = stock.option_chain(exp)
            calls = chain.calls.copy()
            puts = chain.puts.copy()
            calls["expiration"] = exp
            puts["expiration"] = exp
            all_calls.append(calls)
            all_puts.append(puts)
        except Exception:
            continue

    if not all_calls:
        return {"available": False}

    calls_df = pd.concat(all_calls, ignore_index=True)
    puts_df = pd.concat(all_puts, ignore_index=True)

    call_volume = calls_df["volume"].sum()
    put_volume = puts_df["volume"].sum()
    call_oi = calls_df["openInterest"].sum()
    put_oi = puts_df["openInterest"].sum()

    pc_ratio_volume = put_volume / call_volume if call_volume > 0 else None
    pc_ratio_oi = put_oi / call_oi if call_oi > 0 else None

    # Max pain: strike where total option holder losses are maximized
    max_pain = _compute_max_pain(calls_df, puts_df)

    # Unusual activity: options with volume > 3x open interest
    unusual = _find_unusual_activity(calls_df, puts_df)

    return {
        "available": True,
        "expirations_analyzed": list(expirations),
        "call_volume": int(call_volume),
        "put_volume": int(put_volume),
        "call_oi": int(call_oi),
        "put_oi": int(put_oi),
        "pc_ratio_volume": pc_ratio_volume,
        "pc_ratio_oi": pc_ratio_oi,
        "max_pain": max_pain,
        "unusual_activity": unusual,
    }


def _compute_max_pain(calls_df, puts_df):
    strikes = sorted(set(calls_df["strike"].tolist() + puts_df["strike"].tolist()))
    if not strikes:
        return None

    min_pain = float("inf")
    max_pain_strike = None

    call_oi_by_strike = calls_df.groupby("strike")["openInterest"].sum()
    put_oi_by_strike = puts_df.groupby("strike")["openInterest"].sum()

    for strike in strikes:
        pain = 0
        for s, oi in call_oi_by_strike.items():
            if strike > s:
                pain += (strike - s) * oi
        for s, oi in put_oi_by_strike.items():
            if strike < s:
                pain += (s - strike) * oi
        if pain < min_pain:
            min_pain = pain
            max_pain_strike = strike

    return max_pain_strike


def _find_unusual_activity(calls_df, puts_df):
    rows = []
    for label, df in [("CALL", calls_df), ("PUT", puts_df)]:
        mask = (df["volume"] > 0) & (df["openInterest"] > 0)
        active = df[mask].copy()
        if active.empty:
            continue
        active["vol_oi_ratio"] = active["volume"] / active["openInterest"]
        unusual = active[active["vol_oi_ratio"] > 3].nlargest(5, "volume")
        for _, row in unusual.iterrows():
            rows.append({
                "type": label,
                "expiration": row["expiration"],
                "strike": row["strike"],
                "volume": int(row["volume"]),
                "open_interest": int(row["openInterest"]),
                "vol_oi_ratio": round(row["vol_oi_ratio"], 1),
                "implied_vol": round(row["impliedVolatility"] * 100, 1),
            })

    return sorted(rows, key=lambda x: x["volume"], reverse=True)[:10]
