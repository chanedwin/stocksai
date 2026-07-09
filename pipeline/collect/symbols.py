"""Symbol map v1 and point-in-time S&P 500 membership.

Constituents CSV vendored at data/reference/sp500_constituents.csv from
fja05680/sp500 (commit pinned in data/reference/SOURCES.md). Rows are
event-dated: membership at date D is the last row at or before D.
Attribution: fja05680/sp500 (GitHub), reconstructed from public sources.
"""

from functools import lru_cache
from pathlib import Path

import pandas as pd

CONSTITUENTS_CSV = Path("data/reference/sp500_constituents.csv")

# Known renames, old -> current. Extend as sources disagree; versioned in git.
RENAMES = {
    "FB": "META",
}


def normalize(ticker: str) -> str:
    """Canonical form: uppercase, dash share-class separator (BRK.B -> BRK-B)."""
    t = ticker.strip().upper().replace(".", "-")
    return RENAMES.get(t, t)


@lru_cache(maxsize=1)
def _load(csv_path: str = str(CONSTITUENTS_CSV)) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)


def members_at(date: str, csv_path: Path = CONSTITUENTS_CSV) -> set[str]:
    """S&P 500 membership as of date (last event row at or before date)."""
    df = _load(str(csv_path))
    rows = df[df["date"] <= pd.Timestamp(date)]
    if rows.empty:
        raise ValueError(f"{date} predates constituents history ({df['date'].min().date()})")
    tickers = rows.iloc[-1]["tickers"].split(",")
    return {normalize(t) for t in tickers if t}


def verify_constituents(csv_path: Path = CONSTITUENTS_CSV) -> list[str]:
    """Sanity checks from the vendor-verification doc; returns problem strings."""
    problems = []
    df = _load(str(csv_path))
    if not df["date"].is_monotonic_increasing:
        problems.append("dates not sorted")
    counts = df["tickers"].str.split(",").str.len()
    modern = df[df["date"] >= "2004-04-02"]
    modern_counts = counts[modern.index]
    bad = modern[(modern_counts < 495) | (modern_counts > 510)]
    for _, row in bad.iterrows():
        problems.append(f"{row['date'].date()}: {len(row['tickers'].split(','))} members")
    if "TSLA" not in members_at("2020-12-21", csv_path):
        problems.append("TSLA missing at 2020-12-21")
    if "TSLA" in members_at("2020-11-17", csv_path):
        problems.append("TSLA present before 2020-12-21 addition")
    if "SMCI" not in members_at("2024-03-18", csv_path):
        problems.append("SMCI missing at 2024-03-18")
    return problems
