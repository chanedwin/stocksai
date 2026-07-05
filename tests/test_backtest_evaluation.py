import numpy as np
import pandas as pd

from pipeline.backtest import (
    hit_rate,
    long_short_spread,
    monotonicity,
    net_spread,
    quantile_returns,
    rank_ic,
    summarize_ic,
    top_quantile_turnover,
)


def test_rank_ic_matches_hand_computed_spearman():
    panel = pd.DataFrame(
        {
            "date": [pd.Timestamp("2024-01-31")] * 5,
            "score": [1.0, 2.0, 3.0, 4.0, 5.0],
            "label": [0.10, 0.20, 0.30, 0.50, 0.40],
        }
    )
    ic = rank_ic(panel, "score", "label")
    assert np.isclose(ic.iloc[0], 0.9)


def test_planted_signal_recovered_and_distractor_flat(panel):
    strong = summarize_ic(rank_ic(panel, "signal", "label"))
    flat = summarize_ic(rank_ic(panel, "distractor", "label"))
    assert strong["mean_ic"] > 0.5
    assert strong["t_stat"] > 3.0
    assert abs(flat["mean_ic"]) < 0.1
    assert strong["n_dates"] == 24


def test_rank_ic_handles_missing_and_degenerate_dates(panel):
    panel = panel.copy()
    first_date = panel["date"].min()
    panel.loc[panel["date"] == first_date, "label"] = np.nan
    ic = rank_ic(panel, "signal", "label")
    assert first_date not in ic.index
    assert len(ic) == 23

    panel["score_const"] = 1.0
    const_ic = rank_ic(panel, "score_const", "label")
    assert len(const_ic) == 0


def test_quantile_returns_monotonic_for_planted_signal(panel):
    q = quantile_returns(panel, "signal", "label", n_quantiles=10)
    assert q.shape == (24, 10)
    assert monotonicity(q) == 1.0
    spread = long_short_spread(q)
    assert (spread > 0).all()
    assert hit_rate(spread) == 1.0


def test_top_quantile_turnover_counts_membership_changes():
    dates = [pd.Timestamp("2024-01-31")] * 10 + [pd.Timestamp("2024-02-29")] * 10
    tickers = [f"T{i}" for i in range(10)] * 2
    scores_jan = list(range(10))
    scores_feb = list(range(10))
    scores_feb[9], scores_feb[0] = 0, 9
    panel = pd.DataFrame({"date": dates, "ticker": tickers, "score": scores_jan + scores_feb})
    turnover = top_quantile_turnover(panel, "score", quantile=0.1)
    assert np.isclose(turnover.iloc[0], 1.0)

    panel_same = pd.DataFrame({"date": dates, "ticker": tickers, "score": scores_jan * 2})
    turnover_same = top_quantile_turnover(panel_same, "score", quantile=0.1)
    assert np.isclose(turnover_same.iloc[0], 0.0)


def test_net_spread_subtracts_costs():
    dates = pd.date_range("2024-01-31", periods=3, freq="ME")
    spread = pd.Series([0.02, 0.02, 0.02], index=dates)
    turnover = pd.Series([0.5, 0.5], index=dates[1:])
    net = net_spread(spread, turnover, cost_bps_per_side=25)
    assert np.isclose(net.iloc[0], 0.02)
    assert np.isclose(net.iloc[1], 0.02 - 2 * 0.5 * 2 * 0.0025)
