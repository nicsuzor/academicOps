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
            project_root = str(Path(tmpdir) / "project")
            project_hash = hashlib.sha256(project_root.encode()).hexdigest()
            gemini_tmp = Path(tmpdir) / ".gemini" / "tmp" / project_hash

            # Patch Path.home() and Path.cwd()
            with patch.object(Path, "home", return_value=Path(tmpdir)), \
                 patch.object(Path, "cwd", return_value=Path(project_root)):

                # Pass gemini- prefixed session_id to trigger gemini path
                result = session_paths.get_session_status_dir("gemini-test-session")
                self.assertEqual(result, gemini_tmp)

    @patch.dict(os.environ, {"AOPS_SESSION_STATE_DIR": ""}, clear=True)
    def test_get_session_status_dir_claude_fallback(self):
        """When AOPS_SESSION_STATE_DIR not set and session_id is UUID format, use claude path."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = str(Path(tmpdir) / "project")
            # Expected Claude path: ~/.claude/projects/-<cwd-with-dashes>/
            expected_folder = "-" + project_root.replace("/", "-")[1:]
            expected_path = Path(tmpdir) / ".claude" / "projects" / expected_folder

            # Patch Path.home() and Path.cwd()
            with patch.object(Path, "home", return_value=Path(tmpdir)), \
                 patch.object(Path, "cwd", return_value=Path(project_root)):

                # Pass UUID-style session_id to trigger claude path
                result = session_paths.get_session_status_dir("abc123-def456-ghi789")
                self.assertEqual(result, expected_path)

if __name__ == "__main__":
    unittest.main()
