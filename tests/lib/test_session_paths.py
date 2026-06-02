import os
from pathlib import Path
from unittest.mock import patch

import pytest
from lib.session_paths import (
    _is_gemini_session,
    _is_polecat_sandbox,
    _parse_date_arg,
    get_gate_file_path,
    get_hook_log_path,
    get_session_short_hash,
    get_session_status_dir,
)


@pytest.fixture(autouse=True)
def _clear_env_vars(monkeypatch):
    """Clear env vars that leak from live sessions."""
    ENV_VARS_TO_CLEAR = (
        "AOPS_SESSIONS",
        "AOPS_SESSION_STATE_DIR",
        "AOPS_HOOK_LOG_PATH",
        "AOPS_GATE_FILE_ENFORCER",
        "GEMINI_SESSION_ID",
        "POLECAT_CREW_NAME",
        "AOPS_POLECAT_CONTAINER",
    )
    for var in ENV_VARS_TO_CLEAR:
        monkeypatch.delenv(var, raising=False)
    # Pin machine name so tests don't depend on host hostname
    monkeypatch.setenv("AOPS_MACHINE", "testmachine")


class TestParseDateArg:
    """Tests for _parse_date_arg — regression coverage for 00:00 filename collision."""

    def test_none_returns_none(self):
        """None input signals 'use caller default', returns None."""
        assert _parse_date_arg(None) is None

    def test_date_only_string_does_not_produce_midnight(self):
        """A YYYY-MM-DD string must NOT produce a 00:00 timestamp (the collision bug)."""
        result = _parse_date_arg("2026-04-26")
        assert result is not None
        # Pre-fix: fromisoformat("2026-04-26") returned midnight (00:00).
        # Post-fix: time is merged from now(), so it must differ from midnight.
        assert not (result.hour == 0 and result.minute == 0 and result.second == 0), (
            "date-only string produced 00:00 timestamp — filename collision bug is present"
        )

    def test_date_only_string_preserves_date(self):
        """The calendar date in a date-only string must be preserved."""
        result = _parse_date_arg("2026-04-26")
        assert result is not None
        assert result.year == 2026
        assert result.month == 4
        assert result.day == 26

    def test_full_iso_string_with_explicit_time_is_not_modified(self):
        """An ISO-8601 string with explicit time must be returned as-is (no clock merge)."""
        result = _parse_date_arg("2026-01-15T14:30:00+10:00")
        assert result is not None
        assert result.hour == 14
        assert result.minute == 30

    def test_explicit_midnight_iso_string_is_preserved(self):
        """Explicit midnight in a full ISO-8601 string must NOT be replaced by current time."""
        result = _parse_date_arg("2026-01-01T00:00:00+00:00")
        assert result is not None
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0

    def test_invalid_string_returns_none(self):
        """Invalid date strings return None (caller defaults to now)."""
        assert _parse_date_arg("not-a-date") is None

    def test_result_is_timezone_aware(self):
        """All returned datetimes must be timezone-aware."""
        result = _parse_date_arg("2026-04-26")
        assert result is not None
        assert result.tzinfo is not None

        result2 = _parse_date_arg("2026-01-15T14:30:00+10:00")
        assert result2 is not None
        assert result2.tzinfo is not None


class TestIsGeminiSession:
    """Tests for _is_gemini_session function."""

    def test_detection_via_env_var(self):
        """Test detection when GEMINI_SESSION_ID is set."""
        with patch.dict(os.environ, {"GEMINI_SESSION_ID": "some-id"}):
            assert _is_gemini_session("any-id", None) is True

    def test_detection_via_session_id_prefix(self):
        """Test detection when session_id starts with 'gemini-'."""
        assert _is_gemini_session("gemini-12345", None) is True
        assert _is_gemini_session("gemini-abc-123", {}) is True

    def test_detection_via_transcript_path(self):
        """Test detection when transcript_path contains '/.gemini/'."""
        assert (
            _is_gemini_session("some-id", "/home/user/.gemini/tmp/hash/chats/session.json") is True
        )

    def test_detection_via_state_dir_env(self):
        """Test detection when AOPS_SESSION_STATE_DIR contains '/.gemini/'."""
        with patch.dict(os.environ, {"AOPS_SESSION_STATE_DIR": "/home/user/.gemini/tmp/abc/"}):
            assert _is_gemini_session("some-id", None) is True

    def test_claude_session_false(self):
        """Test that normal Claude sessions return False."""
        # Standard UUID
        assert _is_gemini_session("550e8400-e29b-41d4-a716-446655440000", {}) is False
        # No indicators at all
        with patch.dict(os.environ, {}, clear=True):
            assert _is_gemini_session(None, None) is False


class TestGetGateFilePath:
    """Tests for get_gate_file_path function."""

    def test_env_override(self):
        """Test that AOPS_GATE_FILE_<GATE> environment variable overrides the path."""
        with patch.dict(os.environ, {"AOPS_GATE_FILE_ENFORCER": "/tmp/override-enforcer.md"}):
            path = get_gate_file_path("enforcer", "session-123")
            assert str(path) == "/tmp/override-enforcer.md"

    @patch("lib.session_paths.Path.home")
    @patch("lib.session_paths.get_claude_project_folder")
    def test_claude_path_generation(self, mock_project_folder, mock_home, tmp_path):
        """Test path generation for a Claude session."""
        mock_home.return_value = tmp_path
        mock_project_folder.return_value = "-home-user-project"

        session_id = "550e8400-e29b-41d4-a716-446655440000"
        gate = "enforcer"
        date = "2024-05-20T10:00:00+00:00"

        path = get_gate_file_path(gate, session_id, date=date)

        # Unified naming: {YYYYMMDD}-{HHMM}-{session_id}-{shortform}-{slug}-{gate}.md
        # shortform: {repo}-{provider} (no crew here)
        assert "20240520-1000-550e8400-" in str(path)
        assert str(path).endswith("-session-enforcer.md")
        assert "testmachine" not in str(path.name)
        # Provider rides in the filename now (frontmatter remains authoritative).
        assert "-claude-" in str(path.name)
        # Gates land in the session status dir, not in a /logs/ subdir.
        expected_parent = tmp_path / ".claude" / "projects" / "-home-user-project"
        assert expected_parent.exists()
        assert path.parent == expected_parent

    def test_gemini_path_generation(self, tmp_path, monkeypatch):
        """Gemini gate files share the session status dir (no /logs/ split)."""
        gemini_state_dir = tmp_path / ".gemini" / "tmp" / "workspace"
        gemini_state_dir.mkdir(parents=True)
        monkeypatch.setenv("AOPS_SESSION_STATE_DIR", str(gemini_state_dir))
        monkeypatch.setenv("GEMINI_SESSION_ID", "gemini-session-123")

        session_id = "gemini-session-123"
        gate = "enforcer"
        date = "2024-05-20T10:00:00+00:00"

        path = get_gate_file_path(gate, session_id, date=date)

        short_hash = get_session_short_hash(session_id)
        assert f"20240520-1000-{short_hash}-" in str(path)
        assert str(path).endswith("-session-enforcer.md")
        assert "testmachine" not in str(path.name)
        assert "-gemini-" in str(path.name)
        # State dir is the canonical home — no /logs/ subdirectory.
        assert path.parent == gemini_state_dir

    def test_polecat_worker_uuid_as_gemini(self, tmp_path, monkeypatch):
        """UUID session IDs route via Gemini state dir when indicators present."""
        session_id = "550e8400-e29b-41d4-a716-446655440000"
        gemini_state_dir = tmp_path / ".gemini" / "tmp" / "fakehash"
        gemini_state_dir.mkdir(parents=True)

        monkeypatch.setenv("AOPS_SESSION_STATE_DIR", str(gemini_state_dir))
        path = get_gate_file_path("enforcer", session_id, date="2024-05-20T10:00:00+00:00")

        assert "/.gemini/tmp/fakehash" in str(path)
        assert "20240520-1000-550e8400-" in str(path)
        assert str(path).endswith("-session-enforcer.md")
        assert "testmachine" not in str(path.name)
        assert path.parent == gemini_state_dir


class TestPolebcatSandboxRouting:
    """P#82 reproduction tests for polecat-aware path routing.

    The old code had no _is_polecat_sandbox() check and always routed to
    Path.home(). These tests fail on the old code and pass on the new code.
    """

    def test_polecat_sandbox_detection(self, monkeypatch):
        """_is_polecat_sandbox returns True iff AOPS_POLECAT_CONTAINER is set."""
        monkeypatch.delenv("AOPS_POLECAT_CONTAINER", raising=False)
        assert not _is_polecat_sandbox()
        monkeypatch.setenv("AOPS_POLECAT_CONTAINER", "1")
        assert _is_polecat_sandbox()

    @patch("lib.session_paths._polecat_claude_state_dir")
    @patch("lib.session_paths.get_claude_project_folder")
    def test_hook_log_routes_to_polecat_not_home(
        self, mock_project_folder, mock_polecat_dir, monkeypatch, tmp_path
    ):
        """AOPS_POLECAT_CONTAINER set → hook log routes via the polecat state dir.

        All session artefacts (hooks, gates, state) share one dir per session
        now, so the subsystem hint is always ``"state"``.
        """
        monkeypatch.setenv("AOPS_POLECAT_CONTAINER", "1")
        mock_project_folder.return_value = "-home-worker-project"
        mock_polecat_dir.return_value = tmp_path

        path = get_hook_log_path("session-123", date="2024-05-20T10:00:00+00:00")

        mock_polecat_dir.assert_called_with("-home-worker-project", "state")
        assert str(path).startswith(str(tmp_path))
        assert not str(path).startswith(str(Path.home()))

    @patch("lib.session_paths._polecat_claude_state_dir")
    @patch("lib.session_paths.get_claude_project_folder")
    def test_session_status_routes_to_polecat_not_home(
        self, mock_project_folder, mock_polecat_dir, monkeypatch, tmp_path
    ):
        """AOPS_POLECAT_CONTAINER set → session status routes via _polecat_claude_state_dir, not Path.home()."""
        monkeypatch.setenv("AOPS_POLECAT_CONTAINER", "1")
        mock_project_folder.return_value = "-home-worker-project"
        mock_polecat_dir.return_value = tmp_path

        result = get_session_status_dir()

        mock_polecat_dir.assert_called_once_with("-home-worker-project", "state")
        assert result == tmp_path
        assert not str(result).startswith(str(Path.home()))

    @patch("lib.session_paths._polecat_claude_state_dir")
    @patch("lib.session_paths.get_claude_project_folder")
    def test_gate_file_routes_to_polecat_not_home(
        self, mock_project_folder, mock_polecat_dir, monkeypatch, tmp_path
    ):
        """AOPS_POLECAT_CONTAINER set → gate file routes via the polecat state dir."""
        monkeypatch.setenv("AOPS_POLECAT_CONTAINER", "1")
        mock_project_folder.return_value = "-home-worker-project"
        mock_polecat_dir.return_value = tmp_path

        path = get_gate_file_path("enforcer", "session-123", date="2024-05-20T10:00:00+00:00")

        mock_polecat_dir.assert_called_with("-home-worker-project", "state")
        assert str(path).startswith(str(tmp_path))
        assert not str(path).startswith(str(Path.home()))


class TestCoworkSourceRoots:
    def test_cowork_source_roots_darwin(self, monkeypatch):
        import sys

        monkeypatch.setattr(sys, "platform", "darwin")
        from lib.session_paths import cowork_source_roots

        roots = cowork_source_roots()
        assert len(roots) == 1
        assert "Library/Application Support/Claude/local-agent-mode-sessions" in str(roots[0])

    def test_cowork_source_roots_win32(self, monkeypatch):
        import os
        import sys

        monkeypatch.setattr(sys, "platform", "win32")
        monkeypatch.setitem(os.environ, "APPDATA", "C:\\\\Users\\\\Test\\\\AppData\\\\Roaming")
        from lib.session_paths import cowork_source_roots

        roots = cowork_source_roots()
        assert len(roots) == 1
        assert "Claude/local-agent-mode-sessions" in str(roots[0])
        assert "AppData" in str(roots[0])

    def test_cowork_source_roots_linux(self, monkeypatch):
        import sys

        monkeypatch.setattr(sys, "platform", "linux")
        from lib.session_paths import cowork_source_roots

        roots = cowork_source_roots()
        assert len(roots) == 1
        assert ".config/Claude/local-agent-mode-sessions" in str(roots[0])
