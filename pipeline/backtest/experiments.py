import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

SIGNIFICANCE_T_BAR = 3.0
RESERVED_COLUMNS = {"logged_at_utc", "config_hash", "git_commit", "config"}


def config_hash(config):
    canonical = json.dumps(config, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()[:12]


def _git_commit():
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def log_experiment(path, config, metrics):
    """Append one trial to the experiment log. Every run counts, even failures.

    Rows are aligned by column name so runs with different metric sets never
    write values under the wrong header.
    """
    path = Path(path)
    clash = RESERVED_COLUMNS & set(metrics)
    if clash:
        raise ValueError(f"metrics keys collide with reserved columns: {sorted(clash)}")
    row = {
        "logged_at_utc": datetime.now(timezone.utc).isoformat(),
        "config_hash": config_hash(config),
        "git_commit": _git_commit(),
        "config": json.dumps(config, sort_keys=True, default=str),
        **metrics,
    }
    new = pd.DataFrame([row])
    if path.exists():
        new = pd.concat([pd.read_csv(path), new], ignore_index=True)
    new.to_csv(path, index=False)
    return row["config_hash"]


def count_trials(path):
    path = Path(path)
    if not path.exists():
        return 0
    return len(pd.read_csv(path))


def clears_significance_bar(t_stat, bar=SIGNIFICANCE_T_BAR):
    """Harvey-Liu-Zhu style elevated bar for calling a signal real."""
    return bool(t_stat > bar)
