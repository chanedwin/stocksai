"""Pandera schemas for the bronze-to-silver boundary.

validate_to_silver splits a frame into (valid, rejects); nothing drops
silently. Dates are tz-naive UTC per CLAUDE.md.
"""

import pandas as pd
import pandera.pandas as pa

PRICE_SCHEMA = pa.DataFrameSchema(
    {
        "ticker": pa.Column(str),
        "date": pa.Column("datetime64[ns]"),
        "open": pa.Column(float, pa.Check.gt(0)),
        "high": pa.Column(float, pa.Check.gt(0)),
        "low": pa.Column(float, pa.Check.gt(0)),
        "close": pa.Column(float, pa.Check.gt(0)),
        "volume": pa.Column("int64", pa.Check.ge(0)),
    },
    checks=[
        pa.Check(lambda df: df["high"] >= df["low"], error="high >= low"),
        pa.Check(lambda df: df["high"] >= df[["open", "close"]].max(axis=1), error="high bounds open/close"),
        pa.Check(lambda df: df["low"] <= df[["open", "close"]].min(axis=1), error="low bounds open/close"),
        pa.Check(
            lambda df: ~df.duplicated(subset=["ticker", "date"]),
            error="unique (ticker, date)",
        ),
        pa.Check(
            lambda df: df["date"] <= pd.Timestamp.utcnow().tz_localize(None),
            error="no future dates",
        ),
    ],
    strict=False,
    coerce=True,
)


def validate_to_silver(df: pd.DataFrame, schema: pa.DataFrameSchema = PRICE_SCHEMA):
    """Return (valid_rows, rejects). Rejects carry a _reject_reason column."""
    if df.empty:
        return df, df.assign(_reject_reason=pd.Series(dtype=str))
    try:
        return schema.validate(df, lazy=True), df.iloc[0:0].assign(_reject_reason="")
    except pa.errors.SchemaErrors as err:
        bad_idx = set()
        reasons = {}
        for _, failure in err.failure_cases.iterrows():
            idx = failure["index"]
            if idx is None:
                continue
            bad_idx.add(idx)
            reasons.setdefault(idx, []).append(str(failure["check"]))
        bad_idx = sorted(i for i in bad_idx if i in df.index)
        rejects = df.loc[bad_idx].assign(
            _reject_reason=[", ".join(reasons[i]) for i in bad_idx]
        )
        valid = df.drop(index=bad_idx)
        if not valid.empty:
            valid = schema.validate(valid)
        return valid, rejects
