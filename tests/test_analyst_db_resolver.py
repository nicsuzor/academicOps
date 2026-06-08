import sys
from pathlib import Path

# Add the analyst scripts path to sys.path so we can import db_resolver
ANALYST_SCRIPTS = Path(__file__).resolve().parent.parent / "aops-tools" / "skills" / "analyst" / "scripts"
if str(ANALYST_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(ANALYST_SCRIPTS))

import pytest
from db_resolver import get_canonical_db_path, get_project_root


def test_get_project_root_env(monkeypatch):
    """Verify that get_project_root honors CLAUDE_PROJECT_DIR if set."""
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/some/mock/path")
    assert get_project_root() == Path("/some/mock/path")


def test_get_project_root_fallback(monkeypatch):
    """Verify that get_project_root discovers the git root when CLAUDE_PROJECT_DIR is unset."""
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    root = get_project_root().resolve()
    assert (root / ".git").exists(), f"Expected a git root, got {root}"


def test_get_canonical_db_path_success(tmp_path, monkeypatch):
    """Verify that get_canonical_db_path returns the canonical absolute database path."""
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    canonical_db = get_canonical_db_path()
    assert canonical_db == tmp_path / "data" / "warehouse.db"
    assert canonical_db.parent.exists()


def test_get_canonical_db_path_duplicate_raises(tmp_path, monkeypatch):
    """Verify that get_canonical_db_path raises AssertionError if a duplicate db exists."""
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))

    # Create the canonical database file
    canonical_db = tmp_path / "data" / "warehouse.db"
    canonical_db.parent.mkdir(parents=True, exist_ok=True)
    canonical_db.touch()

    # Create a duplicate database file in a different directory (e.g. in some cache folder)
    duplicate_dir = tmp_path / "stale_cache"
    duplicate_dir.mkdir(parents=True, exist_ok=True)
    duplicate_db = duplicate_dir / "warehouse.db"
    duplicate_db.touch()

    # It should raise AssertionError because of the duplicate
    with pytest.raises(AssertionError) as exc_info:
        get_canonical_db_path()

    assert "ERROR: Confusable duplicate cache files found" in str(exc_info.value)
    assert str(duplicate_db) in str(exc_info.value)


def test_get_canonical_db_path_ignored_duplicates(tmp_path, monkeypatch):
    """Verify that get_canonical_db_path ignores duplicate files in hidden/venv/dist directories."""
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))

    # Create the canonical database file
    canonical_db = tmp_path / "data" / "warehouse.db"
    canonical_db.parent.mkdir(parents=True, exist_ok=True)
    canonical_db.touch()

    # Create database files in ignored directories
    for ignored_name in [
        ".git",
        "venv",
        ".venv",
        "node_modules",
        "dist",
        "output",
        "build",
        "_book",
    ]:
        ignored_dir = tmp_path / ignored_name
        ignored_dir.mkdir(parents=True, exist_ok=True)
        (ignored_dir / "warehouse.db").touch()

    # It should NOT raise AssertionError because they are in ignored folders
    canonical_db_resolved = get_canonical_db_path()
    assert canonical_db_resolved == canonical_db
