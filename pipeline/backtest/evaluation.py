import numpy as np
import pandas as pd


def rank_ic(panel, score_col, label_col, date_col="date"):
    """Per-date Spearman correlation between scores and realized labels."""

    def _ic(g):
        ok = g[score_col].notna() & g[label_col].notna()
        s = g.loc[ok, score_col]
        y = g.loc[ok, label_col]
        if len(s) < 3 or s.nunique() < 2 or y.nunique() < 2:
            return np.nan
        return s.rank().corr(y.rank())

    ic = panel.groupby(date_col)[[score_col, label_col]].apply(_ic)
    return ic.dropna()


def overlap_lag(panel, date_col="date", label_end_col="label_end_date"):
    """Max number of later scoring dates that fall inside one label window.

    Zero means labels never overlap across scoring dates and the plain
    t-stat is valid; anything above zero must be passed to summarize_ic
    as nw_lag or the t-stat overstates significance.
    """
    ends = panel.groupby(date_col)[label_end_col].max().sort_index()
    dates = ends.index
    lag = 0
    for date, end in ends.items():
        if pd.isna(end):
            continue
        lag = max(lag, int(((dates > date) & (dates < end)).sum()))
    return lag


def summarize_ic(ic, nw_lag=0):
    """Mean/stability summary of a per-date IC series.

    Per-date ICs are serially correlated whenever label windows overlap
    across scoring dates, which inflates the plain t-stat. Pass
    nw_lag=overlap_lag(panel) to use a Newey-West standard error instead.
    """
    n = int(len(ic))
    if n == 0:
        return {"mean_ic": np.nan, "std_ic": np.nan, "icir": np.nan, "t_stat": np.nan, "n_dates": 0, "nw_lag": int(nw_lag)}
    mean = float(ic.mean())
    std = float(ic.std(ddof=1)) if n > 1 else np.nan
    icir = mean / std if n > 1 and std > 0 else np.nan
    t_stat = np.nan
    if n > 1 and std > 0:
        if nw_lag > 0:
            x = ic.to_numpy(dtype=float) - mean
            long_run_var = float(np.dot(x, x)) / n
            for k in range(1, min(int(nw_lag), n - 1) + 1):
                gamma_k = float(np.dot(x[k:], x[:-k])) / n
                long_run_var += 2.0 * (1.0 - k / (nw_lag + 1.0)) * gamma_k
            if long_run_var > 0:
                t_stat = mean / np.sqrt(long_run_var / n)
        else:
            t_stat = icir * np.sqrt(n)
    return {"mean_ic": mean, "std_ic": std, "icir": icir, "t_stat": t_stat, "n_dates": n, "nw_lag": int(nw_lag)}


def quantile_returns(panel, score_col, label_col, date_col="date", n_quantiles=10):
    """Mean realized label per score quantile per date (1 = lowest scores).

    Dates with fewer valid names than n_quantiles are dropped: assigning
    3 names across 10 buckets puts them all in high quantiles and distorts
    every cross-date aggregate.
    """
    df = panel[[date_col, score_col, label_col]].dropna().copy()
    counts = df.groupby(date_col)[score_col].transform("size")
    df = df[counts >= n_quantiles]
    ranks = df.groupby(date_col)[score_col].rank(pct=True, method="first")
    df["quantile"] = np.ceil(ranks * n_quantiles).clip(1, n_quantiles).astype(int)
    return df.pivot_table(index=date_col, columns="quantile", values=label_col, aggfunc="mean")


def long_short_spread(quantile_df):
    if quantile_df.empty or len(quantile_df.columns) == 0:
        return pd.Series(dtype=float)
    return quantile_df[quantile_df.columns.max()] - quantile_df[quantile_df.columns.min()]


def hit_rate(spread):
    """Share of dates with a positive spread, over defined spreads only."""
    valid = spread.dropna()
    if len(valid) == 0:
        return float("nan")
    return float((valid > 0).mean())


def monotonicity(quantile_df):
    """Fraction of adjacent quantile pairs whose mean label increases."""
    means = quantile_df.mean()
    return float(means.diff().dropna().gt(0).mean())


def top_quantile_turnover(panel, score_col, date_col="date", ticker_col="ticker", quantile=0.1):
    """One-way membership turnover of the top score quantile between dates."""
    df = panel[[date_col, ticker_col, score_col]].dropna()

    def _members(g):
        k = max(1, int(np.ceil(len(g) * quantile)))
        return frozenset(g.nlargest(k, score_col)[ticker_col])

    sets = df.groupby(date_col)[[ticker_col, score_col]].apply(_members).sort_index()
    out = {}
    for prev_date, date in zip(sets.index[:-1], sets.index[1:]):
        current, previous = sets[date], sets[prev_date]
        out[date] = 1.0 - len(current & previous) / len(current)
    return pd.Series(out, dtype=float)


def net_spread(spread, turnover, cost_bps_per_side):
    """Spread net of costs: both legs trade `turnover` one-way, each paying per-side costs.

    Dates without a turnover observation (the first rebalance, always)
    yield NaN rather than trading for free.
    """
    cost = 2.0 * turnover.reindex(spread.index) * 2.0 * cost_bps_per_side / 10_000
    return spread - cost
