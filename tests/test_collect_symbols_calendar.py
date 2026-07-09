import pytest

from pipeline.collect import symbols, trading_calendar


def test_normalize():
    assert symbols.normalize("brk.b") == "BRK-B"
    assert symbols.normalize("BRK-B") == "BRK-B"
    assert symbols.normalize("FB") == "META"
    assert symbols.normalize(" aapl ") == "AAPL"


def test_members_at_known_changes():
    assert "TSLA" not in symbols.members_at("2020-11-17")
    assert "TSLA" in symbols.members_at("2020-12-21")
    assert "SMCI" in symbols.members_at("2024-03-18")


def test_members_at_predates_history():
    with pytest.raises(ValueError):
        symbols.members_at("1990-01-01")


def test_verify_constituents_passes():
    assert symbols.verify_constituents() == []


def test_trading_calendar_holidays():
    assert not trading_calendar.is_trading_day("2026-07-03")  # July 4th observed
    assert trading_calendar.is_trading_day("2026-07-06")
    assert not trading_calendar.is_trading_day("2026-07-04")  # Saturday


def test_last_trading_day():
    assert trading_calendar.last_trading_day("2026-07-05") == "2026-07-02"
    assert trading_calendar.last_trading_day("2026-07-06") == "2026-07-06"


def test_trading_days_range():
    days = trading_calendar.trading_days("2026-06-29", "2026-07-06")
    assert days == [
        "2026-06-29",
        "2026-06-30",
        "2026-07-01",
        "2026-07-02",
        "2026-07-06",
    ]
