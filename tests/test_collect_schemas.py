import pandas as pd

from pipeline.collect.schemas import validate_to_silver


def make_rows(**overrides):
    base = {
        "ticker": ["AAPL", "AAPL"],
        "date": pd.to_datetime(["2026-07-07", "2026-07-08"]),
        "open": [100.0, 101.0],
        "high": [102.0, 103.0],
        "low": [99.0, 100.0],
        "close": [101.0, 102.0],
        "volume": [1_000_000, 1_200_000],
    }
    base.update(overrides)
    return pd.DataFrame(base)


def test_clean_frame_passes():
    valid, rejects = validate_to_silver(make_rows())
    assert len(valid) == 2
    assert rejects.empty


def test_high_below_low_rejected():
    df = make_rows(high=[102.0, 90.0])
    valid, rejects = validate_to_silver(df)
    assert len(valid) == 1
    assert len(rejects) == 1
    assert "high" in rejects["_reject_reason"].iloc[0]


def test_duplicate_ticker_date_rejected():
    df = make_rows(date=pd.to_datetime(["2026-07-07", "2026-07-07"]))
    valid, rejects = validate_to_silver(df)
    assert len(valid) + len(rejects) == 2
    assert len(rejects) >= 1


def test_future_date_rejected():
    df = make_rows(date=pd.to_datetime(["2026-07-07", "2126-01-01"]))
    valid, rejects = validate_to_silver(df)
    assert len(valid) == 1
    assert len(rejects) == 1


def test_negative_volume_rejected():
    df = make_rows(volume=[1_000_000, -5])
    valid, rejects = validate_to_silver(df)
    assert len(valid) == 1
    assert len(rejects) == 1


def test_empty_frame():
    df = make_rows().iloc[0:0]
    valid, rejects = validate_to_silver(df)
    assert valid.empty and rejects.empty
