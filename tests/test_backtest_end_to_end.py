import pandas as pd

from pipeline.backtest import (
    check_ic_alarm,
    rank_ic,
    summarize_ic,
    walk_forward_splits,
)
from tests.conftest import make_panel


def test_walk_forward_evaluation_on_test_folds_only():
    panel = make_panel(n_dates=36, n_tickers=60, signal_strength=0.01, noise=0.03)
    splits = walk_forward_splits(panel, min_train_periods=12, val_periods=6, test_periods=6)
    assert len(splits) == 3

    test_ic = []
    for split in splits:
        test_rows = panel.loc[split.test_idx]
        ic = rank_ic(test_rows, "signal", "label")
        test_ic.append(ic)
    pooled = summarize_ic(pd.concat(test_ic))

    assert pooled["n_dates"] == 18
    assert pooled["mean_ic"] > 0.1
    assert pooled["t_stat"] > 3.0


def test_realistic_weak_signal_passes_ic_alarm():
    panel = make_panel(n_dates=36, n_tickers=100, signal_strength=0.001, noise=0.05)
    result = summarize_ic(rank_ic(panel, "signal", "label"))
    check_ic_alarm(result["mean_ic"])
    assert result["mean_ic"] < 0.10
