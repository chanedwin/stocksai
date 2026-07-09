"""Data-layout paths and atomic partition writes.

Bronze is append-only raw payloads; silver is validated Parquet. Writes go
to a .partial path and are atomically renamed so a crashed run never leaves
a half-written partition (CLAUDE.md checkpoint rule).
"""

import shutil
from pathlib import Path

DATA_ROOT = Path("data")


def bronze_path(source: str, partition: str, root: Path = DATA_ROOT) -> Path:
    return root / "bronze" / source / partition


def silver_path(dataset: str, year: int, root: Path = DATA_ROOT) -> Path:
    return root / "silver" / dataset / f"year={year}"


def rejects_path(dataset: str, root: Path = DATA_ROOT) -> Path:
    return root / "silver" / "_rejects" / dataset


def atomic_write(target: Path, write_fn) -> Path:
    """Write via write_fn(partial_path), then atomically swap into place.

    write_fn receives a Path that does not exist yet; it may create a file
    or a directory there. On success the partial replaces target; on error
    the partial is removed and target is left untouched.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".partial")
    if partial.exists():
        _remove(partial)
    try:
        write_fn(partial)
        if not partial.exists():
            raise FileNotFoundError(f"write_fn did not create {partial}")
        backup = target.with_name(target.name + ".replaced")
        if target.exists():
            target.rename(backup)
        try:
            partial.rename(target)
        finally:
            if backup.exists():
                _remove(backup)
        return target
    except Exception:
        if partial.exists():
            _remove(partial)
        raise


def _remove(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()
