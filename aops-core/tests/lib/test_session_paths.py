import os
import pytest
from pathlib import Path
from unittest.mock import patch
from lib.session_paths import _is_gemini_session, get_gate_file_path, get_session_short_hash

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
        input_data = {"transcript_path": "/home/user/.gemini/tmp/hash/chats/session.json"}
        assert _is_gemini_session("some-id", input_data) is True

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
        with patch.dict(os.environ, {"AOPS_GATE_FILE_HYDRATION": "/tmp/override-hydration.md"}):
            path = get_gate_file_path("hydration", "session-123")
            assert str(path) == "/tmp/override-hydration.md"

    @patch("lib.session_paths.Path.home")
    @patch("lib.session_paths.get_claude_project_folder")
    def test_claude_path_generation(self, mock_project_folder, mock_home, tmp_path):
        """Test path generation for a Claude session."""
        mock_home.return_value = tmp_path
        mock_project_folder.return_value = "-home-user-project"

        session_id = "550e8400-e29b-41d4-a716-446655440000"
        gate = "custodiet"
        date = "2024-05-20"

        path = get_gate_file_path(gate, session_id, date=date)

        # Expected: ~/.claude/projects/<project>/<date>-<shorthash>-<gate>.md
        # Short hash for "550e8400..." is "550e8400"
        expected_path = tmp_path / ".claude" / "projects" / "-home-user-project" / "20240520-550e8400-custodiet.md"
        assert path == expected_path
        # Verify parent directory was created (via mkdir(parents=True, exist_ok=True))
        assert expected_path.parent.exists()

    @patch("lib.session_paths._is_gemini_session")
    @patch("lib.session_paths.get_gemini_logs_dir")
    def test_gemini_path_generation(self, mock_logs_dir, mock_is_gemini, tmp_path):
        """Test path generation for a Gemini session."""
        mock_is_gemini.return_value = True
        mock_logs_dir.return_value = tmp_path / "gemini-logs"
        (tmp_path / "gemini-logs").mkdir(parents=True)

        session_id = "gemini-session-123"
        gate = "qa"
        date = "2024-05-20"

        path = get_gate_file_path(gate, session_id, date=date)

        # Short hash for "gemini-session-123" will be a SHA256 prefix because of '-'
        short_hash = get_session_short_hash(session_id)
        expected_path = tmp_path / "gemini-logs" / f"20240520-{short_hash}-qa.md"

        assert path == expected_path

    def test_polecat_worker_uuid_as_gemini(self, tmp_path):
        """Test that UUID session IDs are handled as Gemini if indicators are present."""
        session_id = "550e8400-e29b-41d4-a716-446655440000"
        # Setup fake Gemini state dir
        gemini_state_dir = tmp_path / ".gemini" / "tmp" / "fakehash"
        gemini_logs_dir = gemini_state_dir / "logs"
        gemini_logs_dir.mkdir(parents=True)

        # Use AOPS_SESSION_STATE_DIR to trigger Gemini detection for a UUID session
        with patch.dict(os.environ, {"AOPS_SESSION_STATE_DIR": str(gemini_state_dir)}):
            path = get_gate_file_path("critic", session_id, date="2024-05-20")

            assert "/.gemini/tmp/fakehash/logs" in str(path)
            assert "20240520-550e8400-critic.md" in str(path)
            assert path.parent == gemini_logs_dir

    def test_gemini_missing_logs_dir_raises_error(self):
        """Test that it raises ValueError if Gemini is detected but logs dir cannot be found."""
        with patch("lib.session_paths._is_gemini_session", return_value=True):
            with patch("lib.session_paths.get_gemini_logs_dir", return_value=None):
                with pytest.raises(ValueError, match="Gemini session detected but no logs directory configured"):
                    get_gate_file_path("hydration", "some-id")
