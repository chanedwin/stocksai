from pathlib import Path

import pytest

from pipeline.collect import storage


def test_failed_swap_restores_previous_data(tmp_path, monkeypatch):
    target = tmp_path / "data.parquet"
    storage.atomic_write(target, lambda p: p.write_text("v1"))
    original_rename = Path.rename

    def flaky_rename(self, dst):
        if self.name.endswith(".partial"):
            raise OSError("swap failed")
        return original_rename(self, dst)

    monkeypatch.setattr(Path, "rename", flaky_rename)
    with pytest.raises(OSError):
        storage.atomic_write(target, lambda p: p.write_text("v2"))
    monkeypatch.undo()
    assert target.read_text() == "v1"
    assert list(tmp_path.iterdir()) == [target]


def test_atomic_write_file(tmp_path):
    target = tmp_path / "part" / "data.parquet"
    storage.atomic_write(target, lambda p: p.write_text("v1"))
    assert target.read_text() == "v1"
    assert not target.with_name("data.parquet.partial").exists()


def test_atomic_write_replaces_existing(tmp_path):
    target = tmp_path / "data.parquet"
    storage.atomic_write(target, lambda p: p.write_text("v1"))
    storage.atomic_write(target, lambda p: p.write_text("v2"))
    assert target.read_text() == "v2"
    assert list(tmp_path.iterdir()) == [target]


def test_failed_write_leaves_target_untouched(tmp_path):
    target = tmp_path / "data.parquet"
    storage.atomic_write(target, lambda p: p.write_text("v1"))

    def boom(p):
        p.write_text("partial garbage")
        raise RuntimeError("network died")

    with pytest.raises(RuntimeError):
        storage.atomic_write(target, boom)
    assert target.read_text() == "v1"
    assert list(tmp_path.iterdir()) == [target]


def test_atomic_write_directory_partition(tmp_path):
    target = tmp_path / "year=2026"

    def write_dir(p):
        p.mkdir()
        (p / "a.parquet").write_text("rows")

    storage.atomic_write(target, write_dir)
    assert (target / "a.parquet").read_text() == "rows"


def test_write_fn_creating_nothing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        storage.atomic_write(tmp_path / "x", lambda p: None)


def test_paths():
    assert str(storage.bronze_path("tiingo_prices", "ingest_date=2026-07-09")) == (
        "data/bronze/tiingo_prices/ingest_date=2026-07-09"
    )
    assert str(storage.silver_path("prices", 2026)) == "data/silver/prices/year=2026"
    assert str(storage.rejects_path("prices")) == "data/silver/_rejects/prices"
