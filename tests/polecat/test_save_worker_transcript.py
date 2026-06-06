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

_original_cli = sys.modules.get("cli")

try:
    # Force re-import if cli was already partially loaded
    sys.modules.pop("cli", None)
    from cli import (
        _extract_gemini_sessions,
        _find_real_transcript,
        save_worker_transcript,
    )
finally:
    # Remove the stub-loaded cli so other test modules get a clean import.
    sys.modules.pop("cli", None)
    # Restore the real cli module if it was present before stub loading.
    # Without this, patch("cli.*") in test_cli_docker.py resolves a fresh
    # import that doesn't match the _is_colima_env.__globals__ dict from
    # the earlier real import, silently defeating the mocks.
    if _original_cli is not None:
        sys.modules["cli"] = _original_cli
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
# _find_real_transcript — Gemini/antigravity (agy) sessions
#
# Regression: agy runs recorded ``real_transcript_path: null`` because the
# finder globbed only ``*.jsonl`` while agy writes ``session-*.json`` (single
# ``.json``). The finder must locate those AND prefer the canonical ``chats/``
# copy over the ephemeral ``.gemini-tmp/`` staging copy.
# ---------------------------------------------------------------------------


class TestFindRealTranscriptGemini:
    def test_finds_gemini_session_json(self, tmp_path: Path) -> None:
        run = tmp_path / "run"
        chats = run / "chats"
        chats.mkdir(parents=True)
        sess = chats / "session-abc123.json"
        sess.write_text('{"role":"user","content":"hi"}\n')

        result = _find_real_transcript(run)
        assert result == sess

    def test_excludes_polecat_stub_keeps_gemini_session(self, tmp_path: Path) -> None:
        run = tmp_path / "run"
        run.mkdir()
        # polecat's own lifecycle stub is a .jsonl that must be ignored.
        (run / "polecat-session-deadbeef.jsonl").write_text('{"phase":"started"}\n')
        chats = run / "chats"
        chats.mkdir()
        sess = chats / "session-x.json"
        sess.write_text("{}\n")

        result = _find_real_transcript(run)
        assert result == sess

    def test_prefers_canonical_chats_over_gemini_tmp_staging(self, tmp_path: Path) -> None:
        run = tmp_path / "run"
        staging = run / ".gemini-tmp" / "hashdir" / "chats"
        staging.mkdir(parents=True)
        (staging / "session-x.json").write_text("{}\n")
        canonical = run / "chats"
        canonical.mkdir(parents=True)
        canon = canonical / "session-x.json"
        canon.write_text("{}\n")

        result = _find_real_transcript(run)
        assert result == canon
        assert ".gemini-tmp" not in result.parts


# ---------------------------------------------------------------------------
# _extract_gemini_sessions — promotes .gemini-tmp/session-*.json to chats/,
# and must be idempotent (it runs once before the transcript save and again in
# the run's finally block; a second pass must not spawn prefixed duplicates).
# ---------------------------------------------------------------------------


class TestExtractGeminiSessions:
    def _seed_staging(self, tmp_path: Path, name: str = "session-x.json") -> Path:
        run = tmp_path / "run"
        src = run / ".gemini-tmp" / "abc123hash" / "chats"
        src.mkdir(parents=True)
        (src / name).write_text('{"session":"data"}\n')
        return run

    def test_extracts_session_to_chats(self, tmp_path: Path) -> None:
        run = self._seed_staging(tmp_path)
        _extract_gemini_sessions(run)
        assert (run / "chats" / "session-x.json").exists()

    def test_idempotent_no_duplicate_on_second_pass(self, tmp_path: Path) -> None:
        run = self._seed_staging(tmp_path)
        _extract_gemini_sessions(run)
        _extract_gemini_sessions(run)  # second pass (the finally-block call)

        chats_files = sorted((run / "chats").glob("session-*.json"))
        assert len(chats_files) == 1
        assert chats_files[0].name == "session-x.json"

    def test_distinct_sessions_same_basename_both_kept(self, tmp_path: Path) -> None:
        # Two genuinely different sessions sharing a basename (different hash
        # dirs, different content) must both survive — disambiguated, not lost.
        run = tmp_path / "run"
        a = run / ".gemini-tmp" / "hashA" / "chats"
        b = run / ".gemini-tmp" / "hashB" / "chats"
        a.mkdir(parents=True)
        b.mkdir(parents=True)
        (a / "session-x.json").write_text('{"a":1}\n')
        (b / "session-x.json").write_text('{"b":22222}\n')  # different size

        _extract_gemini_sessions(run)
        _extract_gemini_sessions(run)  # idempotent across repeats

        kept = sorted((run / "chats").glob("*session-x.json"))
        assert len(kept) == 2


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
