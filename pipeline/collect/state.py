"""State DB for collectors: watermarks, run log, quota ledger.

Single SQLite file at data/state/pipeline.sqlite. All timestamps are UTC
ISO 8601. Watermarks are keyed (source, ticker); market-level sources use
ticker="*".
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DB = Path("data/state/pipeline.sqlite")

SCHEMA = """
CREATE TABLE IF NOT EXISTS watermarks (
    source TEXT NOT NULL,
    ticker TEXT NOT NULL,
    watermark TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (source, ticker)
);
CREATE TABLE IF NOT EXISTS run_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL,
    rows INTEGER,
    detail TEXT
);
CREATE TABLE IF NOT EXISTS quota_ledger (
    source TEXT NOT NULL,
    consumer TEXT NOT NULL,
    date TEXT NOT NULL,
    used INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (source, consumer, date)
);
"""


def connect(db_path: Path = DEFAULT_DB) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_watermark(conn, source: str, ticker: str = "*") -> str | None:
    row = conn.execute(
        "SELECT watermark FROM watermarks WHERE source=? AND ticker=?",
        (source, ticker),
    ).fetchone()
    return row[0] if row else None


def set_watermark(conn, source: str, watermark: str, ticker: str = "*") -> None:
    conn.execute(
        "INSERT INTO watermarks (source, ticker, watermark, updated_at) "
        "VALUES (?, ?, ?, ?) "
        "ON CONFLICT(source, ticker) DO UPDATE SET "
        "watermark=excluded.watermark, updated_at=excluded.updated_at",
        (source, ticker, watermark, _now()),
    )
    conn.commit()


def start_run(conn, source: str) -> int:
    cur = conn.execute(
        "INSERT INTO run_log (source, started_at, status) VALUES (?, ?, 'running')",
        (source, _now()),
    )
    conn.commit()
    return cur.lastrowid


def finish_run(conn, run_id: int, status: str, rows: int = 0, detail: str = "") -> None:
    conn.execute(
        "UPDATE run_log SET finished_at=?, status=?, rows=?, detail=? WHERE id=?",
        (_now(), status, rows, detail, run_id),
    )
    conn.commit()


def quota_used(conn, source: str, date: str) -> int:
    row = conn.execute(
        "SELECT COALESCE(SUM(used), 0) FROM quota_ledger WHERE source=? AND date=?",
        (source, date),
    ).fetchone()
    return row[0]


def spend_quota(
    conn, source: str, consumer: str, date: str, n: int, daily_limit: int
) -> bool:
    """Reserve n requests for consumer; False if the shared budget lacks room."""
    if quota_used(conn, source, date) + n > daily_limit:
        return False
    conn.execute(
        "INSERT INTO quota_ledger (source, consumer, date, used) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(source, consumer, date) DO UPDATE SET used = used + excluded.used",
        (source, consumer, date, n),
    )
    conn.commit()
    return True


def missed_days(conn, source: str, expected_dates: list[str]) -> list[str]:
    """Expected run dates with no successful run_log entry, for health alerts."""
    done = {
        row[0][:10]
        for row in conn.execute(
            "SELECT started_at FROM run_log WHERE source=? AND status='success'",
            (source,),
        )
    }
    return [d for d in expected_dates if d not in done]
