import os
from unittest.mock import patch

import pytest
from lib.session_paths import _is_gemini_session, get_gate_file_path, get_session_short_hash


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
    )
    for var in ENV_VARS_TO_CLEAR:
        monkeypatch.delenv(var, raising=False)
    # Pin machine name so tests don't depend on host hostname
    monkeypatch.setenv("AOPS_MACHINE", "testmachine")


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
        # shortform here (no crew): {repo} only — machine/provider moved to frontmatter
        assert "20240520-1000-550e8400-" in str(path)
        assert str(path).endswith("-session-enforcer.md")
        assert "testmachine" not in str(path.name)
        assert str(path.name).count("-claude-") == 0
        # Verify parent directory was created (via mkdir(parents=True, exist_ok=True))
        expected_parent = tmp_path / ".claude" / "projects" / "-home-user-project"
        assert expected_parent.exists()

    @patch("lib.session_paths._is_gemini_session")
    @patch("lib.session_paths.get_gemini_logs_dir")
    def test_gemini_path_generation(self, mock_logs_dir, mock_is_gemini, tmp_path):
        """Test path generation for a Gemini session."""
        mock_is_gemini.return_value = True
        mock_logs_dir.return_value = tmp_path / "gemini-logs"
        (tmp_path / "gemini-logs").mkdir(parents=True)

        session_id = "gemini-session-123"
        gate = "enforcer"
        date = "2024-05-20T10:00:00+00:00"

        # Set GEMINI_SESSION_ID so naming-layer provider detection agrees with
        # the path-level _is_gemini_session mock.
        with patch.dict(os.environ, {"GEMINI_SESSION_ID": session_id}):
            path = get_gate_file_path(gate, session_id, date=date)

        short_hash = get_session_short_hash(session_id)
        assert f"20240520-1000-{short_hash}-" in str(path)
        assert str(path).endswith("-session-enforcer.md")
        assert "testmachine" not in str(path.name)
        assert str(path.name).count("-gemini-") == 0

    def test_polecat_worker_uuid_as_gemini(self, tmp_path):
        """Test that UUID session IDs are handled as Gemini if indicators are present."""
        session_id = "550e8400-e29b-41d4-a716-446655440000"
        # Setup fake Gemini state dir
        gemini_state_dir = tmp_path / ".gemini" / "tmp" / "fakehash"
        gemini_logs_dir = gemini_state_dir / "logs"
        gemini_logs_dir.mkdir(parents=True)

        # Use AOPS_SESSION_STATE_DIR to trigger Gemini detection for a UUID session
        with patch.dict(os.environ, {"AOPS_SESSION_STATE_DIR": str(gemini_state_dir)}):
            path = get_gate_file_path("enforcer", session_id, date="2024-05-20T10:00:00+00:00")

            assert "/.gemini/tmp/fakehash/logs" in str(path)
            assert "20240520-1000-550e8400-" in str(path)
            assert str(path).endswith("-session-enforcer.md")
            assert "testmachine" not in str(path.name)
            assert path.parent == gemini_logs_dir

    def test_gemini_missing_logs_dir_raises_error(self):
        """Test that it raises ValueError if Gemini is detected but logs dir cannot be found."""
        with patch("lib.session_paths._is_gemini_session", return_value=True):
            with patch("lib.session_paths.get_gemini_logs_dir", return_value=None):
                with pytest.raises(
                    ValueError, match="Gemini session detected but no logs directory configured"
                ):
                    get_gate_file_path("enforcer", "some-id")
