import numpy as np
import pandas as pd

from pipeline.backtest import (
    hit_rate,
    long_short_spread,
    monotonicity,
    net_spread,
    overlap_lag,
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


def test_net_spread_subtracts_costs_and_flags_missing_turnover():
    dates = pd.date_range("2024-01-31", periods=3, freq="ME")
    spread = pd.Series([0.02, 0.02, 0.02], index=dates)
    turnover = pd.Series([0.5, 0.5], index=dates[1:])
    net = net_spread(spread, turnover, cost_bps_per_side=25)
    assert pd.isna(net.iloc[0])
    assert np.isclose(net.iloc[1], 0.02 - 2 * 0.5 * 2 * 0.0025)


def test_summarize_ic_hand_computed_formulas():
    ic = pd.Series([0.1, 0.2, 0.3])
    res = summarize_ic(ic)
    assert np.isclose(res["mean_ic"], 0.2)
    assert np.isclose(res["std_ic"], 0.1)
    assert np.isclose(res["icir"], 2.0)
    assert np.isclose(res["t_stat"], 2.0 * np.sqrt(3))
    assert res["n_dates"] == 3


def test_summarize_ic_newey_west_hand_computed():
    ic = pd.Series([0.1, 0.2, 0.3])
    res = summarize_ic(ic, nw_lag=1)
    assert np.isclose(res["t_stat"], 3.0 * np.sqrt(2))
    assert res["nw_lag"] == 1


def test_newey_west_shrinks_t_under_positive_autocorrelation():
    ic = pd.Series([1.0, 1.0, 1.0, 0.0, 0.0, 0.0])
    naive = summarize_ic(ic)["t_stat"]
    corrected = summarize_ic(ic, nw_lag=2)["t_stat"]
    assert corrected < naive


def test_overlap_lag_detects_scoring_finer_than_horizon():
    monthly = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-31", periods=6, freq="ME"),
            "label_end_date": pd.date_range("2024-01-31", periods=6, freq="ME") + pd.Timedelta(days=21),
        }
    )
    assert overlap_lag(monthly) == 0

    weekly = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-05", periods=8, freq="7D"),
            "label_end_date": pd.date_range("2024-01-05", periods=8, freq="7D") + pd.Timedelta(days=21),
        }
    )
    assert overlap_lag(weekly) == 2


def test_hit_rate_ignores_undefined_spreads_and_handles_mixed():
    assert np.isclose(hit_rate(pd.Series([0.01, np.nan, 0.02, np.nan])), 1.0)
    assert np.isclose(hit_rate(pd.Series([0.02, -0.01, 0.03, -0.02])), 0.5)
    assert np.isnan(hit_rate(pd.Series([np.nan, np.nan])))


def test_monotonicity_on_non_monotone_means():
    quantile_df = pd.DataFrame({1: [1.0], 2: [3.0], 3: [2.0], 4: [4.0]})
    assert np.isclose(monotonicity(quantile_df), 2 / 3)


def test_quantile_returns_drops_dates_smaller_than_quantile_count(panel):
    small_date = pd.Timestamp("2022-06-30")
    small = pd.DataFrame(
        {
            "date": [small_date] * 3,
            "ticker": ["A", "B", "C"],
            "signal": [1.0, 2.0, 3.0],
            "distractor": [0.0, 0.0, 0.0],
            "label": [0.01, 0.02, 0.03],
            "label_end_date": [small_date + pd.Timedelta(days=21)] * 3,
        }
    )
    q = quantile_returns(pd.concat([panel, small], ignore_index=True), "signal", "label", n_quantiles=10)
    assert small_date not in q.index
    assert q.shape == (24, 10)


def test_long_short_spread_on_empty_quantiles_returns_empty(panel):
    all_nan = panel.copy()
    all_nan["label"] = np.nan
    q = quantile_returns(all_nan, "signal", "label")
    spread = long_short_spread(q)
    assert len(spread) == 0


def test_top_quantile_turnover_with_bucket_larger_than_one():
    dates = [pd.Timestamp("2024-01-31")] * 20 + [pd.Timestamp("2024-02-29")] * 20
    tickers = [f"T{i:02d}" for i in range(20)] * 2
    scores_jan = list(range(20))
    scores_feb = list(range(20))
    scores_feb[15], scores_feb[16] = -1, -2
    scores_feb[0], scores_feb[1] = 100, 99
    panel = pd.DataFrame({"date": dates, "ticker": tickers, "score": scores_jan + scores_feb})
    turnover = top_quantile_turnover(panel, "score", quantile=0.25)
    assert np.isclose(turnover.iloc[0], 2 / 5)
