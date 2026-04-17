"""Unit tests for save_worker_transcript and _find_real_transcript."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Import the functions under test from polecat/cli.py.
#
# cli.py has heavy top-level imports (click, manager, observability, etc.)
# that aren't installed in the lightweight test environment.  We stub every
# non-stdlib module it imports at the top level so collection succeeds.
# ---------------------------------------------------------------------------

TESTS_DIR = Path(__file__).parent.resolve()
REPO_ROOT = TESTS_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT / "polecat"))
sys.path.insert(0, str(REPO_ROOT / "aops-core"))

_MODS_TO_STUB = [
    "click",
    "manager",
    "observability",
    "observability.metrics",
    "validation",
    "lib",
    "lib.agent_env",
    "lib.paths",
    "docker_builder",
    "pkb_bridge",
    "rich",
    "rich.console",
    "rich.table",
    "rich.panel",
    "psutil",
]

_saved: dict[str, object] = {}
for _mod in _MODS_TO_STUB:
    if _mod not in sys.modules:
        _saved[_mod] = None
        sys.modules[_mod] = MagicMock()
    else:
        _saved[_mod] = sys.modules[_mod]

try:
    # Force re-import if cli was already partially loaded
    sys.modules.pop("cli", None)
    from cli import _find_real_transcript, save_worker_transcript
finally:
    # Remove the stub-loaded cli so other test modules get a clean import.
    sys.modules.pop("cli", None)
    # Restore original modules; remove stubs we inserted.
    for _mod, _orig in _saved.items():
        if _orig is None:
            sys.modules.pop(_mod, None)
        else:
            sys.modules[_mod] = _orig


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def session_layout(tmp_path: Path) -> dict[str, Path]:
    """Create a minimal session directory layout with a fake real transcript."""
    home_dir = tmp_path / "home"
    home_dir.mkdir()

    run_session_dir = tmp_path / "sessions" / "polecats" / "task-abc123" / "myproject"
    workspace = run_session_dir / "-workspace"
    workspace.mkdir(parents=True)

    # Write a fake real transcript (~1KB)
    real_transcript = workspace / "deadbeef-1234-5678-abcd-000000000000.jsonl"
    real_transcript.write_text('{"type":"assistant","message":"hello"}\n' * 30)

    return {
        "home_dir": home_dir,
        "run_session_dir": run_session_dir,
        "real_transcript": real_transcript,
    }


# ---------------------------------------------------------------------------
# _find_real_transcript
# ---------------------------------------------------------------------------


class TestFindRealTranscript:
    def test_finds_newest_transcript(self, session_layout: dict[str, Path]) -> None:
        result = _find_real_transcript(session_layout["run_session_dir"])
        assert result is not None
        assert result == session_layout["real_transcript"]

    def test_returns_none_when_no_session_dir(self) -> None:
        assert _find_real_transcript(None) is None

    def test_returns_none_when_no_workspace(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "sessions" / "polecats" / "task-xyz"
        run_dir.mkdir(parents=True)
        assert _find_real_transcript(run_dir) is None

    def test_returns_none_when_workspace_empty(self, tmp_path: Path) -> None:
        workspace = tmp_path / "sessions" / "polecats" / "task-xyz" / "-workspace"
        workspace.mkdir(parents=True)
        assert _find_real_transcript(tmp_path / "sessions" / "polecats" / "task-xyz") is None

    def test_picks_newest_by_mtime(self, tmp_path: Path) -> None:
        workspace = tmp_path / "run" / "-workspace"
        workspace.mkdir(parents=True)

        old = workspace / "old.jsonl"
        old.write_text('{"old": true}\n')
        new = workspace / "new.jsonl"
        new.write_text('{"new": true}\n')
        # Pin old's mtime deterministically in the past rather than relying on sleep.
        os.utime(old, (old.stat().st_atime, new.stat().st_mtime - 1))

        result = _find_real_transcript(tmp_path / "run")
        assert result is not None
        assert result.name == "new.jsonl"


# ---------------------------------------------------------------------------
# save_worker_transcript
# ---------------------------------------------------------------------------


class TestSaveWorkerTranscript:
    @pytest.fixture(autouse=True)
    def _block_lib_paths(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Ensure ``from lib.paths import ...`` raises ImportError inside
        save_worker_transcript so it falls back to home_dir / "transcripts"."""
        monkeypatch.setitem(sys.modules, "lib.paths", None)

    def test_stub_includes_real_transcript_fields(self, session_layout: dict[str, Path]) -> None:
        stub_path = save_worker_transcript(
            task_id="task-abc123",
            stdout="some output",
            stderr="",
            exit_code=0,
            agent_type="claude",
            home_dir=session_layout["home_dir"],
            real_transcript=session_layout["real_transcript"],
        )

        assert stub_path.exists()
        entry = json.loads(stub_path.read_text().strip().split("\n")[-1])

        real = session_layout["real_transcript"]
        assert entry["real_transcript_path"] == str(real)
        assert entry["real_transcript_size_bytes"] == real.stat().st_size
        assert entry["real_transcript_size_bytes"] > 0

    def test_stub_without_session_dir_has_null_fields(self, tmp_path: Path) -> None:
        home_dir = tmp_path / "home"
        home_dir.mkdir()

        stub_path = save_worker_transcript(
            task_id="task-xyz789",
            stdout="output",
            stderr="",
            exit_code=1,
            agent_type="claude",
            home_dir=home_dir,
        )

        entry = json.loads(stub_path.read_text().strip().split("\n")[-1])
        assert entry["real_transcript_path"] is None
        assert entry["real_transcript_size_bytes"] is None

    def test_stub_with_empty_workspace_has_null_fields(self, tmp_path: Path) -> None:
        home_dir = tmp_path / "home"
        home_dir.mkdir()

        stub_path = save_worker_transcript(
            task_id="task-empty",
            stdout="",
            stderr="",
            exit_code=0,
            agent_type="claude",
            home_dir=home_dir,
            real_transcript=None,
        )

        entry = json.loads(stub_path.read_text().strip().split("\n")[-1])
        assert entry["real_transcript_path"] is None
        assert entry["real_transcript_size_bytes"] is None
