import pandas as pd
import pytest

from pipeline.backtest import (
    clears_significance_bar,
    config_hash,
    count_trials,
    log_experiment,
)


def test_config_hash_is_order_insensitive_and_distinct():
    a = config_hash({"features": ["mom_12_1"], "horizon": 21})
    b = config_hash({"horizon": 21, "features": ["mom_12_1"]})
    c = config_hash({"horizon": 5, "features": ["mom_12_1"]})
    assert a == b
    assert a != c
    assert len(a) == 12


def test_log_experiment_appends_and_counts(tmp_path):
    log_path = tmp_path / "experiments.csv"
    assert count_trials(log_path) == 0
    config = {"features": ["mom_12_1"], "horizon": 21}
    first_hash = log_experiment(log_path, config, {"mean_ic": 0.021, "t_stat": 1.4})
    log_experiment(log_path, {"horizon": 5}, {"mean_ic": 0.002, "t_stat": 0.1})
    assert count_trials(log_path) == 2
    logged = pd.read_csv(log_path)
    assert list(logged["config_hash"])[0] == first_hash == config_hash(config)
    assert set(["logged_at_utc", "git_commit", "config", "mean_ic", "t_stat"]) <= set(logged.columns)


def test_log_aligns_differing_metric_sets_by_name(tmp_path):
    log_path = tmp_path / "experiments.csv"
    log_experiment(log_path, {"a": 1}, {"mean_ic": 0.02, "t_stat": 1.1})
    log_experiment(log_path, {"a": 2}, {"sharpe": 0.4})
    logged = pd.read_csv(log_path)
    assert logged.loc[1, "sharpe"] == 0.4
    assert pd.isna(logged.loc[1, "mean_ic"])
    assert pd.isna(logged.loc[0, "sharpe"])
    assert logged.loc[0, "mean_ic"] == 0.02


def test_metrics_cannot_clobber_provenance_columns(tmp_path):
    log_path = tmp_path / "experiments.csv"
    with pytest.raises(ValueError):
        log_experiment(log_path, {"a": 1}, {"config_hash": "EVIL", "mean_ic": 0.01})
    assert count_trials(log_path) == 0


def test_significance_bar():
    assert not clears_significance_bar(2.5)
    assert not clears_significance_bar(3.0)
    assert clears_significance_bar(3.2)
