import numpy as np

LEAKY_IC_THRESHOLD = 0.10


class LeakageAlarm(AssertionError):
    pass


def check_ic_alarm(mean_ic, threshold=LEAKY_IC_THRESHOLD):
    """A mean rank IC above the threshold is treated as leakage, not success."""
    if abs(mean_ic) > threshold:
        raise LeakageAlarm(
            f"mean rank IC {mean_ic:.3f} exceeds {threshold:.2f}: "
            "audit joins and features for lookahead before believing this result"
        )


def shuffled_labels(panel, label_col, date_col="date", seed=0):
    """Labels permuted across tickers within each date: the leak-free null."""
    rng = np.random.default_rng(seed)
    return panel.groupby(date_col)[label_col].transform(
        lambda s: rng.permutation(s.to_numpy())
    )


def check_shuffle_null(mean_ic_shuffled, tolerance=0.02):
    """Scores against within-date shuffled labels must show near-zero IC."""
    if abs(mean_ic_shuffled) > tolerance:
        raise LeakageAlarm(
            f"shuffled-label mean IC {mean_ic_shuffled:.3f} exceeds {tolerance}: "
            "the evaluation harness itself leaks"
        )


def check_knowledge_time(panel, knowledge_col, date_col="date"):
    """No feature may be dated after the as-of date it is used on."""
    bad = panel.loc[panel[knowledge_col] > panel[date_col]]
    if len(bad):
        raise LeakageAlarm(
            f"{len(bad)} rows have {knowledge_col} after {date_col}; "
            "features would use information not yet public"
        )
