import pandas as pd
import pytest

from pipeline.backtest import (
    LEAKY_IC_THRESHOLD,
    LeakageAlarm,
    check_ic_alarm,
    check_knowledge_time,
    check_shuffle_null,
    rank_ic,
    shuffled_labels,
    summarize_ic,
)


def test_deliberate_leak_trips_the_ic_alarm(panel):
    panel = panel.copy()
    panel["leaky_score"] = panel["label"]
    result = summarize_ic(rank_ic(panel, "leaky_score", "label"))
    with pytest.raises(LeakageAlarm):
        check_ic_alarm(result["mean_ic"])


def test_honest_small_ic_passes_the_alarm():
    check_ic_alarm(0.04)
    check_ic_alarm(-0.04)


def test_ic_alarm_boundary_and_sign():
    assert LEAKY_IC_THRESHOLD == 0.10
    check_ic_alarm(0.10)
    with pytest.raises(LeakageAlarm):
        check_ic_alarm(0.101)
    with pytest.raises(LeakageAlarm):
        check_ic_alarm(-0.11)


def test_shuffled_labels_pass_the_null_check_even_on_small_panels(panel):
    panel = panel.copy()
    panel["label_shuffled"] = shuffled_labels(panel, "label", seed=11)
    ic_shuffled = rank_ic(panel, "signal", "label_shuffled")
    check_shuffle_null(ic_shuffled)

    honest = summarize_ic(rank_ic(panel, "signal", "label"))
    assert honest["mean_ic"] > 0.5


def test_shuffle_preserves_within_date_values(panel):
    shuffled = shuffled_labels(panel, "label", seed=3)
    for date, group in panel.groupby("date"):
        assert sorted(shuffled[group.index]) == sorted(group["label"])


def test_shuffle_null_check_raises_when_mean_is_many_ses_from_zero():
    biased = pd.Series([0.05, 0.06, 0.04, 0.05, 0.06, 0.04])
    with pytest.raises(LeakageAlarm):
        check_shuffle_null(biased)
    with pytest.raises(LeakageAlarm):
        check_shuffle_null(-biased)
    flat = pd.Series([0.05, -0.05, 0.04, -0.04, 0.03, -0.03])
    check_shuffle_null(flat)


def test_knowledge_time_violation_is_caught(panel):
    panel = panel.copy()
    panel["knowledge_time"] = panel["date"] - pd.Timedelta(days=1)
    panel.loc[panel.index[1], "knowledge_time"] = panel.loc[panel.index[1], "date"]
    check_knowledge_time(panel, "knowledge_time")
    panel.loc[panel.index[0], "knowledge_time"] = panel.loc[panel.index[0], "date"] + pd.Timedelta(days=1)
    with pytest.raises(LeakageAlarm):
        check_knowledge_time(panel, "knowledge_time")


def test_missing_knowledge_time_is_a_violation(panel):
    panel = panel.copy()
    panel["knowledge_time"] = panel["date"] - pd.Timedelta(days=1)
    panel.loc[panel.index[0], "knowledge_time"] = pd.NaT
    with pytest.raises(LeakageAlarm):
        check_knowledge_time(panel, "knowledge_time")
