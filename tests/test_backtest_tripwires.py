import pandas as pd
import pytest

from pipeline.backtest import (
    LeakageAlarm,
    check_ic_alarm,
    check_knowledge_time,
    check_shuffle_null,
    rank_ic,
    shuffled_labels,
    summarize_ic,
)
from tests.conftest import make_panel


def test_deliberate_leak_trips_the_ic_alarm(panel):
    panel = panel.copy()
    panel["leaky_score"] = panel["label"]
    result = summarize_ic(rank_ic(panel, "leaky_score", "label"))
    with pytest.raises(LeakageAlarm):
        check_ic_alarm(result["mean_ic"])


def test_honest_small_ic_passes_the_alarm():
    check_ic_alarm(0.04)
    check_ic_alarm(-0.04)


def test_shuffled_labels_produce_near_zero_ic():
    panel = make_panel(n_dates=60, n_tickers=100)
    panel["label_shuffled"] = shuffled_labels(panel, "label", seed=11)
    result = summarize_ic(rank_ic(panel, "signal", "label_shuffled"))
    check_shuffle_null(result["mean_ic"], tolerance=0.05)
    assert abs(result["mean_ic"]) < 0.05

    honest = summarize_ic(rank_ic(panel, "signal", "label"))
    assert honest["mean_ic"] > 0.5


def test_shuffle_preserves_within_date_values(panel):
    shuffled = shuffled_labels(panel, "label", seed=3)
    for date, group in panel.groupby("date"):
        assert sorted(shuffled[group.index]) == sorted(group["label"])


def test_shuffle_null_check_raises_on_large_ic():
    with pytest.raises(LeakageAlarm):
        check_shuffle_null(0.08)


def test_knowledge_time_violation_is_caught(panel):
    panel = panel.copy()
    panel["knowledge_time"] = panel["date"] - pd.Timedelta(days=1)
    check_knowledge_time(panel, "knowledge_time")
    panel.loc[panel.index[0], "knowledge_time"] = panel.loc[panel.index[0], "date"] + pd.Timedelta(days=1)
    with pytest.raises(LeakageAlarm):
        check_knowledge_time(panel, "knowledge_time")
