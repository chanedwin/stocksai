from dataclasses import dataclass

import pandas as pd


@dataclass
class Split:
    fold: int
    train_idx: pd.Index
    val_idx: pd.Index
    test_idx: pd.Index
    val_start: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp


def walk_forward_splits(
    panel,
    date_col="date",
    label_end_col="label_end_date",
    min_train_periods=36,
    val_periods=12,
    test_periods=12,
    embargo=None,
):
    """Expanding-window walk-forward splits with label purging.

    A row enters training only if its label window closes before the
    validation block starts (minus the embargo gap), so overlapping forward
    labels cannot carry evaluation-period information into training. Rows
    with a missing label end date never enter training or validation.
    """
    embargo = pd.Timedelta(0) if embargo is None else pd.Timedelta(embargo)
    dates = pd.DatetimeIndex(sorted(pd.unique(panel[date_col])))
    if min_train_periods < 1 or val_periods < 0 or test_periods < 1:
        raise ValueError("periods must be positive (val_periods may be 0)")

    splits = []
    fold = 0
    start = min_train_periods
    while start + val_periods + test_periods <= len(dates):
        val_start = dates[start]
        test_start = dates[start + val_periods]
        test_end = dates[start + val_periods + test_periods - 1]

        train_mask = panel[label_end_col] < (val_start - embargo)
        val_mask = (
            (panel[date_col] >= val_start)
            & (panel[date_col] < test_start)
            & (panel[label_end_col] < (test_start - embargo))
        )
        test_mask = (panel[date_col] >= test_start) & (panel[date_col] <= test_end)

        splits.append(
            Split(
                fold=fold,
                train_idx=panel.index[train_mask],
                val_idx=panel.index[val_mask],
                test_idx=panel.index[test_mask],
                val_start=val_start,
                test_start=test_start,
                test_end=test_end,
            )
        )
        fold += 1
        start += test_periods
    return splits
