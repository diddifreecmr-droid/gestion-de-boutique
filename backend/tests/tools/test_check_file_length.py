"""Script de CI « aucun fichier .py au-delà de 200 lignes »."""

from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from tools.check_file_length import DEFAULT_MAX_LINES, count_lines, find_violations, main


def _write(path: Path, lines: int) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x = 1\n" * lines, encoding="utf-8")
    return path


@given(st.integers(min_value=0, max_value=500), st.booleans())
def test_count_lines_matches_line_count(lines: int, trailing_newline: bool) -> None:
    text = "\n".join(["a"] * lines) + ("\n" if trailing_newline and lines else "")
    assert count_lines(text) == lines


def test_file_at_limit_passes_and_above_fails(tmp_path: Path) -> None:
    _write(tmp_path / "ok.py", DEFAULT_MAX_LINES)
    too_long = _write(tmp_path / "pkg" / "long.py", DEFAULT_MAX_LINES + 1)
    _write(tmp_path / "ignored.txt", 1000)
    violations = find_violations([tmp_path], DEFAULT_MAX_LINES)
    assert [(v.path, v.lines) for v in violations] == [(too_long, DEFAULT_MAX_LINES + 1)]


def test_main_exit_codes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write(tmp_path / "a.py", 3)
    assert main(["--max", "3", str(tmp_path)]) == 0
    assert "OK" in capsys.readouterr().out
    assert main(["--max", "2", str(tmp_path)]) == 1
    assert "a.py: 3 lignes (max 2)" in capsys.readouterr().err


def test_missing_root_fails_explicitly(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main([str(tmp_path / "absent")]) == 2
    assert "Racine introuvable" in capsys.readouterr().err


def test_project_sources_respect_the_limit() -> None:
    backend = Path(__file__).resolve().parents[2]
    assert find_violations([backend / "app", backend / "tests"], DEFAULT_MAX_LINES) == []
