import unittest
from unittest.mock import patch, MagicMock
import os
import sys
from pathlib import Path
import hashlib

# Add aops-core to path
AOPS_CORE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AOPS_CORE_DIR))

from lib import session_paths

class TestSessionPaths(unittest.TestCase):
    
    @patch.dict(os.environ, {"AOPS_SESSION_STATE_DIR": "/custom/path"})
    def test_get_session_status_dir_env_var(self):
        # Should respect env var
        with patch("pathlib.Path.mkdir"): # prevent actual mkdir
            path = session_paths.get_session_status_dir()
            self.assertEqual(str(path), "/custom/path")

    @patch.dict(os.environ, {"AOPS_SESSION_STATE_DIR": ""}, clear=True)
    def test_get_session_status_dir_gemini_fallback(self):
        """When AOPS_SESSION_STATE_DIR not set and session_id starts with gemini-, use gemini path."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a fake gemini tmp structure
            project_root = Path(tmpdir) / "project"
            project_root.mkdir(parents=True, exist_ok=True)
            project_hash = hashlib.sha256(str(project_root.resolve()).encode()).hexdigest()
            gemini_tmp = Path(tmpdir) / ".gemini" / "tmp" / project_hash

            # Patch Path.home() and Path.cwd() - cwd must return a real path for resolve()
            with patch.object(Path, "home", return_value=Path(tmpdir)), \
                 patch.object(Path, "cwd", return_value=project_root):

                # Pass gemini- prefixed session_id to trigger gemini path
                result = session_paths.get_session_status_dir("gemini-test-session")
                self.assertEqual(result, gemini_tmp)

    @patch.dict(os.environ, {"AOPS_SESSION_STATE_DIR": ""}, clear=True)
    def test_get_session_status_dir_claude_fallback(self):
        """When AOPS_SESSION_STATE_DIR not set and session_id is UUID format, use claude path."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "project"
            project_root.mkdir(parents=True, exist_ok=True)
            # Expected Claude path: ~/.claude/projects/-<cwd-with-dashes>/
            resolved_root = str(project_root.resolve())
            expected_folder = "-" + resolved_root.replace("/", "-")[1:]
            expected_path = Path(tmpdir) / ".claude" / "projects" / expected_folder

            # Patch Path.home() and Path.cwd() - cwd must return a real path for resolve()
            with patch.object(Path, "home", return_value=Path(tmpdir)), \
                 patch.object(Path, "cwd", return_value=project_root):

                # Pass UUID-style session_id to trigger claude path
                result = session_paths.get_session_status_dir("abc123-def456-ghi789")
                self.assertEqual(result, expected_path)

    @patch.dict(os.environ, {"AOPS_SESSION_STATE_DIR": ""}, clear=True)
    def test_get_session_status_dir_gemini_via_transcript_path(self):
        """When transcript_path contains /.gemini/, detect as Gemini session."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a fake gemini tmp structure with chats subdirectory
            gemini_hash = "02446fdfe96b1eb171c290b1b3da4c0aafff4108395fdefaac4dd1a188242b94"
            gemini_base = Path(tmpdir) / ".gemini" / "tmp" / gemini_hash
            gemini_chats = gemini_base / "chats"
            gemini_chats.mkdir(parents=True, exist_ok=True)

            # Transcript path as Gemini CLI would provide it
            transcript_path = str(gemini_chats / "session-07328230-44d4-414b-9fec-191a6eec0948.json")

            # Patch Path.home()
            with patch.object(Path, "home", return_value=Path(tmpdir)):
                # Pass UUID session_id (no gemini- prefix) but with Gemini transcript_path
                input_data = {"transcript_path": transcript_path}
                result = session_paths.get_session_status_dir(
                    "07328230-44d4-414b-9fec-191a6eec0948", input_data=input_data
                )
                # Should detect Gemini from transcript_path and return gemini_base
                self.assertEqual(result, gemini_base)

    def test_is_gemini_session_transcript_path(self):
        """_is_gemini_session detects Gemini via transcript_path."""
        # UUID session_id (no gemini- prefix) with Gemini transcript_path
        result = session_paths._is_gemini_session(
            "07328230-44d4-414b-9fec-191a6eec0948",
            {"transcript_path": "/home/user/.gemini/tmp/hash/chats/session.json"}
        )
        self.assertTrue(result)

    def test_is_gemini_session_prefix(self):
        """_is_gemini_session detects Gemini via session_id prefix."""
        result = session_paths._is_gemini_session("gemini-2026-01-01-abc123", None)
        self.assertTrue(result)

    def test_is_gemini_session_claude(self):
        """_is_gemini_session returns False for Claude sessions."""
        result = session_paths._is_gemini_session(
            "abc123-def456-ghi789",
            {"transcript_path": "/home/user/.claude/projects/foo/bar.json"}
        )
        self.assertFalse(result)

if __name__ == "__main__":
    unittest.main()
