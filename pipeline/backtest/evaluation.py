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


def summarize_ic(ic):
    n = int(len(ic))
    if n == 0:
        return {"mean_ic": np.nan, "std_ic": np.nan, "icir": np.nan, "t_stat": np.nan, "n_dates": 0}
    mean = float(ic.mean())
    std = float(ic.std(ddof=1)) if n > 1 else np.nan
    icir = mean / std if n > 1 and std > 0 else np.nan
    t_stat = icir * np.sqrt(n) if n > 1 and std > 0 else np.nan
    return {"mean_ic": mean, "std_ic": std, "icir": icir, "t_stat": t_stat, "n_dates": n}


def quantile_returns(panel, score_col, label_col, date_col="date", n_quantiles=10):
    """Mean realized label per score quantile per date (1 = lowest scores)."""
    df = panel[[date_col, score_col, label_col]].dropna().copy()
    ranks = df.groupby(date_col)[score_col].rank(pct=True, method="first")
    df["quantile"] = np.ceil(ranks * n_quantiles).clip(1, n_quantiles).astype(int)
    return df.pivot_table(index=date_col, columns="quantile", values=label_col, aggfunc="mean")


def long_short_spread(quantile_df):
    return quantile_df[quantile_df.columns.max()] - quantile_df[quantile_df.columns.min()]


def hit_rate(spread):
    return float((spread > 0).mean())


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
    """Spread net of costs: both legs trade `turnover` one-way, each paying per-side costs."""
    cost = 2.0 * turnover.reindex(spread.index).fillna(0.0) * 2.0 * cost_bps_per_side / 10_000
    return spread - cost
