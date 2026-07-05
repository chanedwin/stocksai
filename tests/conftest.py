import numpy as np
import pandas as pd
import pytest


def make_panel(n_dates=24, n_tickers=50, signal_strength=0.05, noise=0.02, seed=7):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2020-01-31", periods=n_dates, freq="ME")
    frames = []
    for date in dates:
        signal = rng.normal(size=n_tickers)
        frames.append(
            pd.DataFrame(
                {
                    "date": date,
                    "ticker": [f"T{i:03d}" for i in range(n_tickers)],
                    "signal": signal,
                    "distractor": rng.normal(size=n_tickers),
                    "label": signal_strength * signal + rng.normal(scale=noise, size=n_tickers),
                    "label_end_date": date + pd.Timedelta(days=21),
                }
            )
        )
    return pd.concat(frames, ignore_index=True)


@pytest.fixture
def panel():
    return make_panel()
