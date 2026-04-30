"""Tests that client_type ("claude" / "gemini") flows from --client into JSONL logs.

Bug context: hook JSONL showed model=unknown for all polecat sessions. Without
client_type in the log entry, claude vs gemini sessions were indistinguishable
except by session-ID prefix. (task-c5d2e2da)

Coverage:
1. normalize_input(client_type="claude") -> ctx.client_type == "claude"
2. normalize_input(client_type="gemini") -> ctx.client_type == "gemini"
3. normalize_input() with no client_type -> ctx.client_type is None
   (NOT the string "unknown" -- that is a separate bug.)
4. JSONL log entry written by unified_logger.log_hook_event includes the
   client_type field with the populated value.
"""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Setup path to include aops-core
AOPS_CORE_DIR = Path(__file__).parent.parent.parent
if str(AOPS_CORE_DIR) not in sys.path:
    sys.path.insert(0, str(AOPS_CORE_DIR))

from hooks.router import HookRouter
from hooks.unified_logger import log_hook_event


@pytest.fixture
def router(monkeypatch):
    monkeypatch.setattr("hooks.router.get_session_data", lambda: {})
    return HookRouter()


@pytest.fixture
def temp_claude_projects(monkeypatch):
    """Create temporary Claude projects directory for hook log writes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        projects_dir = Path(tmpdir) / ".claude" / "projects"
        projects_dir.mkdir(parents=True)

        monkeypatch.setattr(Path, "home", lambda: Path(tmpdir))

        monkeypatch.delenv("AOPS_HOOK_LOG_PATH", raising=False)
        monkeypatch.delenv("AOPS_SESSION_STATE_DIR", raising=False)
        monkeypatch.delenv("AOPS_SESSIONS", raising=False)
        monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
        monkeypatch.delenv("GEMINI_SESSION_ID", raising=False)

        yield tmpdir


class TestClientTypeOnContext:
    """normalize_input populates ctx.client_type from the client_type kwarg."""

    def test_client_type_claude(self, router):
        raw = {"session_id": "test-claude-session"}
        with patch("hooks.router.persist_session_data"):
            ctx = router.normalize_input(raw, client_type="claude")
        assert ctx.client_type == "claude"

    def test_client_type_gemini(self, router):
        raw = {"session_id": "test-gemini-session"}
        with patch("hooks.router.persist_session_data"):
            ctx = router.normalize_input(raw, client_type="gemini")
        assert ctx.client_type == "gemini"

    def test_client_type_absent_is_none(self, router):
        """When --client is absent, client_type must be None (not 'unknown')."""
        raw = {"session_id": "test-no-client-session"}
        with patch("hooks.router.persist_session_data"):
            ctx = router.normalize_input(raw)
        assert ctx.client_type is None


class TestClientTypeInJSONL:
    """log_hook_event writes client_type into the JSONL log entry."""

    def _read_log_entries(self, projects_root: str) -> list[dict]:
        log_files = list(Path(projects_root).rglob("*-hooks.jsonl"))
        assert len(log_files) == 1, f"Expected 1 log file, found {len(log_files)}"
        with log_files[0].open() as f:
            return [json.loads(line) for line in f if line.strip()]

    def test_jsonl_contains_client_type_claude(self, router, temp_claude_projects):
        raw = {"session_id": "test-jsonl-claude"}
        with patch("hooks.router.persist_session_data"):
            ctx = router.normalize_input(raw, client_type="claude")

        log_hook_event(ctx)

        entries = self._read_log_entries(temp_claude_projects)
        assert len(entries) == 1
        assert entries[0]["client_type"] == "claude"

    def test_jsonl_contains_client_type_gemini(self, router, temp_claude_projects):
        raw = {"session_id": "test-jsonl-gemini"}
        with patch("hooks.router.persist_session_data"):
            ctx = router.normalize_input(raw, client_type="gemini")

        log_hook_event(ctx)

        entries = self._read_log_entries(temp_claude_projects)
        assert len(entries) == 1
        assert entries[0]["client_type"] == "gemini"

    def test_jsonl_client_type_null_when_absent(self, router, temp_claude_projects):
        """JSONL must show client_type: null (not 'unknown') when --client absent."""
        raw = {"session_id": "test-jsonl-no-client"}
        with patch("hooks.router.persist_session_data"):
            ctx = router.normalize_input(raw)

        log_hook_event(ctx)

        entries = self._read_log_entries(temp_claude_projects)
        assert len(entries) == 1
        assert "client_type" in entries[0], "client_type field must be present in JSONL"
        assert entries[0]["client_type"] is None
