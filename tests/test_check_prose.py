import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "check_prose.py"


def run(path):
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(path)], capture_output=True, text=True
    )


def test_clean_file_passes(tmp_path):
    f = tmp_path / "clean.md"
    f.write_text("The data shows a rise in short interest, not a signal.\n")
    assert run(f).returncode == 0


def test_em_dash_fails(tmp_path):
    f = tmp_path / "dash.md"
    f.write_text("Prices rose — then fell.\n")
    result = run(f)
    assert result.returncode == 1
    assert "em dash" in result.stdout


def test_banned_word_fails(tmp_path):
    f = tmp_path / "word.md"
    f.write_text("Let us delve into the numbers.\n")
    result = run(f)
    assert result.returncode == 1
    assert "delve" in result.stdout


def test_banned_phrase_fails(tmp_path):
    f = tmp_path / "phrase.md"
    f.write_text("In order to compute returns, fetch prices.\n")
    result = run(f)
    assert result.returncode == 1


def test_code_blocks_skipped(tmp_path):
    f = tmp_path / "code.md"
    f.write_text("```python\nx = 'in order to'  # — em dash here\n```\n")
    assert run(f).returncode == 0
