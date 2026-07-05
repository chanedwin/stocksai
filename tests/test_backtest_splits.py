import pandas as pd

from pipeline.backtest import walk_forward_splits


def test_expanding_folds_are_disjoint_and_grow(panel):
    splits = walk_forward_splits(
        panel, min_train_periods=6, val_periods=3, test_periods=3
    )
    assert len(splits) == 5
    train_sizes = []
    for split in splits:
        assert len(set(split.train_idx) & set(split.val_idx)) == 0
        assert len(set(split.train_idx) & set(split.test_idx)) == 0
        assert len(set(split.val_idx) & set(split.test_idx)) == 0
        test_dates = panel.loc[split.test_idx, "date"]
        assert test_dates.min() == split.test_start
        assert test_dates.max() == split.test_end
        train_sizes.append(len(split.train_idx))
    assert train_sizes == sorted(train_sizes)


def test_purging_drops_train_rows_whose_labels_cross_into_validation(panel):
    splits = walk_forward_splits(
        panel, min_train_periods=6, val_periods=3, test_periods=3
    )
    val_start = splits[0].val_start
    dates = sorted(panel["date"].unique())
    last_train_date = dates[5]
    leaky = pd.DataFrame(
        {
            "date": [last_train_date],
            "ticker": ["LEAKY"],
            "signal": [0.0],
            "distractor": [0.0],
            "label": [0.0],
            "label_end_date": [val_start + pd.Timedelta(days=5)],
        }
    )
    panel_with_leak = pd.concat([panel, leaky], ignore_index=True)
    splits_with_leak = walk_forward_splits(
        panel_with_leak, min_train_periods=6, val_periods=3, test_periods=3
    )
    assert splits_with_leak[0].val_start == val_start
    leaky_idx = panel_with_leak.index[panel_with_leak["ticker"] == "LEAKY"][0]
    assert leaky_idx not in splits_with_leak[0].train_idx
    clean_sibling = panel_with_leak.index[
        (panel_with_leak["date"] == last_train_date) & (panel_with_leak["ticker"] == "T000")
    ][0]
    assert clean_sibling in splits_with_leak[0].train_idx


def test_embargo_widens_the_gap_before_validation(panel):
    no_embargo = walk_forward_splits(
        panel, min_train_periods=6, val_periods=3, test_periods=3
    )
    with_embargo = walk_forward_splits(
        panel, min_train_periods=6, val_periods=3, test_periods=3, embargo="30D"
    )
    assert len(with_embargo[0].train_idx) < len(no_embargo[0].train_idx)
    train_label_ends = panel.loc[with_embargo[0].train_idx, "label_end_date"]
    assert (train_label_ends < with_embargo[0].val_start - pd.Timedelta("30D")).all()


def test_rows_without_label_end_never_train(panel):
    panel = panel.copy()
    live_row_date = panel["date"].max()
    panel.loc[panel["date"] == live_row_date, "label_end_date"] = pd.NaT
    splits = walk_forward_splits(
        panel, min_train_periods=6, val_periods=3, test_periods=3
    )
    nat_idx = set(panel.index[panel["label_end_date"].isna()])
    for split in splits:
        assert len(nat_idx & set(split.train_idx)) == 0
