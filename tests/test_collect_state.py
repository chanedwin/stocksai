from pipeline.collect import state


def make_conn(tmp_path):
    return state.connect(tmp_path / "pipeline.sqlite")


def test_watermark_roundtrip(tmp_path):
    conn = make_conn(tmp_path)
    assert state.get_watermark(conn, "tiingo_prices", "AAPL") is None
    state.set_watermark(conn, "tiingo_prices", "2026-07-08", "AAPL")
    assert state.get_watermark(conn, "tiingo_prices", "AAPL") == "2026-07-08"
    state.set_watermark(conn, "tiingo_prices", "2026-07-09", "AAPL")
    assert state.get_watermark(conn, "tiingo_prices", "AAPL") == "2026-07-09"


def test_watermark_market_level_default(tmp_path):
    conn = make_conn(tmp_path)
    state.set_watermark(conn, "fred", "2026-07-01")
    assert state.get_watermark(conn, "fred") == "2026-07-01"
    assert state.get_watermark(conn, "fred", "AAPL") is None


def test_run_log(tmp_path):
    conn = make_conn(tmp_path)
    run_id = state.start_run(conn, "option_chains")
    state.finish_run(conn, run_id, "success", rows=42)
    row = conn.execute(
        "SELECT status, rows, finished_at FROM run_log WHERE id=?", (run_id,)
    ).fetchone()
    assert row[0] == "success"
    assert row[1] == 42
    assert row[2] is not None


def test_quota_shared_across_consumers(tmp_path):
    conn = make_conn(tmp_path)
    assert state.spend_quota(conn, "alphavantage", "earnings", "2026-07-09", 20, 25)
    assert not state.spend_quota(conn, "alphavantage", "estimates", "2026-07-09", 10, 25)
    assert state.spend_quota(conn, "alphavantage", "estimates", "2026-07-09", 5, 25)
    assert state.quota_used(conn, "alphavantage", "2026-07-09") == 25
    assert state.spend_quota(conn, "alphavantage", "earnings", "2026-07-10", 25, 25)


def test_missed_days(tmp_path):
    conn = make_conn(tmp_path)
    run_id = state.start_run(conn, "option_chains")
    state.finish_run(conn, run_id, "success")
    today = conn.execute("SELECT started_at FROM run_log WHERE id=?", (run_id,)).fetchone()[0][:10]
    missing = state.missed_days(conn, "option_chains", [today, "2020-01-02"])
    assert missing == ["2020-01-02"]
