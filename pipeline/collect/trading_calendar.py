"""Exchange calendar helpers (XNYS via exchange_calendars). Dates are ISO strings."""

from functools import lru_cache

import exchange_calendars as xcals
import pandas as pd


@lru_cache(maxsize=1)
def _cal():
    return xcals.get_calendar("XNYS")


def is_trading_day(date: str) -> bool:
    return _cal().is_session(date)


def trading_days(start: str, end: str) -> list[str]:
    return [d.date().isoformat() for d in _cal().sessions_in_range(start, end)]


def last_trading_day(date: str) -> str:
    """The trading session at or before date."""
    ts = pd.Timestamp(date)
    return _cal().date_to_session(ts, direction="previous").date().isoformat()
