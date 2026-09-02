"""Unit tests for scripts/no_em_dashes.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "no_em_dashes.py"


def run(*paths: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *(str(p) for p in paths)],
        capture_output=True,
        text=True,
    )


def test_script_exists():
    assert SCRIPT.is_file(), f"Expected script at {SCRIPT}"


def test_rewrites_body_and_frontmatter(tmp_path: Path):
    """The whole file is rewritten, including YAML frontmatter."""
    target = tmp_path / "doc.md"
    target.write_text(
        "---\ndescription: a — b\n---\n\n# Title\n\nbody — text — here\n",
        encoding="utf-8",
    )

    res = run(target)

    assert res.returncode == 1, res.stderr
    assert target.read_text(encoding="utf-8") == (
        "---\ndescription: a -- b\n---\n\n# Title\n\nbody -- text -- here\n"
    )
    assert "3 em-dash(es) rewritten" in res.stdout


def test_clean_file_untouched(tmp_path: Path):
    target = tmp_path / "clean.md"
    original = "# Title\n\nSome text -- with double hyphens.\n"
    target.write_text(original, encoding="utf-8")

    res = run(target)

    assert res.returncode == 0
    assert res.stdout == ""
    assert target.read_text(encoding="utf-8") == original


def test_reports_every_changed_file(tmp_path: Path):
    dirty = tmp_path / "dirty.md"
    clean = tmp_path / "clean.md"
    dirty.write_text("a — b\n", encoding="utf-8")
    clean.write_text("a -- b\n", encoding="utf-8")

    res = run(dirty, clean)

    assert res.returncode == 1
    assert str(dirty) in res.stdout
    assert str(clean) not in res.stdout
