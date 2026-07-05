import numpy as np
import pandas as pd

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


def check_shuffle_null(ic_shuffled, max_abs_t=4.0):
    """The per-date IC series from a shuffled-label run must be statistically flat.

    Alarms when the mean IC is more than max_abs_t standard errors from
    zero, so the bar scales with panel size instead of false-alarming on
    small panels or waving through large ones.
    """
    ic = pd.Series(ic_shuffled).dropna()
    n = len(ic)
    if n < 2:
        return
    mean = float(ic.mean())
    std = float(ic.std(ddof=1))
    if std > 0:
        t = mean / (std / np.sqrt(n))
    else:
        t = np.inf if mean != 0 else 0.0
    if abs(t) > max_abs_t:
        raise LeakageAlarm(
            f"shuffled-label IC t-stat {t:.2f} exceeds {max_abs_t}: "
            "the evaluation harness itself leaks"
        )


def check_knowledge_time(panel, knowledge_col, date_col="date"):
    """No feature may be dated after, or missing, the as-of date it is used on.

    A missing knowledge time is a violation, not a pass: it is the common
    symptom of exactly the broken joins this tripwire exists to catch.
    """
    known = panel[knowledge_col]
    bad = panel.loc[known.isna() | (known > panel[date_col])]
    if len(bad):
        raise LeakageAlarm(
            f"{len(bad)} rows have {knowledge_col} missing or after {date_col}; "
            "features would use information not provably public"
        )
