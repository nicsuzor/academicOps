import hashlib
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

# Add aops-core to path
AOPS_CORE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AOPS_CORE_DIR))

from lib import session_paths


class TestSessionPaths(unittest.TestCase):
    @patch.dict(os.environ, {"AOPS_SESSION_STATE_DIR": "/custom/path"})
    def test_get_session_status_dir_env_var(self):
        # Should respect env var
        with patch("pathlib.Path.mkdir"):  # prevent actual mkdir
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
            with (
                patch.object(Path, "home", return_value=Path(tmpdir)),
                patch.object(Path, "cwd", return_value=project_root),
            ):
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
            with (
                patch.object(Path, "home", return_value=Path(tmpdir)),
                patch.object(Path, "cwd", return_value=project_root),
            ):
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
            transcript_path = str(
                gemini_chats / "session-07328230-44d4-414b-9fec-191a6eec0948.json"
            )

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
            {"transcript_path": "/home/user/.gemini/tmp/hash/chats/session.json"},
        )
        self.assertTrue(result)

    def test_is_gemini_session_prefix(self):
        """_is_gemini_session detects Gemini via session_id prefix."""
        result = session_paths._is_gemini_session("gemini-2026-01-01-abc123", None)
        self.assertTrue(result)

    @patch.dict(os.environ, {"GEMINI_SESSION_ID": "test-session-id"})
    def test_is_gemini_session_env_var(self):
        """_is_gemini_session detects Gemini via GEMINI_SESSION_ID env var."""
        result = session_paths._is_gemini_session(None, None)
        self.assertTrue(result)

    def test_is_gemini_session_claude(self):
        """_is_gemini_session returns False for Claude sessions."""
        result = session_paths._is_gemini_session(
            "abc123-def456-ghi789",
            {"transcript_path": "/home/user/.claude/projects/foo/bar.json"},
        )
        self.assertFalse(result)

    @patch.dict(
        os.environ,
        {"AOPS_SESSION_STATE_DIR": "/home/user/.gemini/tmp/abc123hash/"},
        clear=True,
    )
    def test_is_gemini_session_state_dir_fallback(self):
        """_is_gemini_session detects Gemini via AOPS_SESSION_STATE_DIR when no transcript_path.

        This is the polecat worker case: worker runs in isolated worktree without
        transcript_path in input_data, but AOPS_SESSION_STATE_DIR was set by router.
        Regression test for GH#467.
        """
        # UUID session_id (no gemini- prefix), no transcript_path, but state dir is Gemini
        result = session_paths._is_gemini_session(
            "07328230-44d4-414b-9fec-191a6eec0948",
            {},  # No transcript_path - simulating polecat worker
        )
        self.assertTrue(result, "Should detect Gemini from AOPS_SESSION_STATE_DIR")

    @patch.dict(
        os.environ,
        {"AOPS_SESSION_STATE_DIR": ""},
        clear=True,
    )
    def test_is_gemini_session_state_dir_no_false_positive(self):
        """_is_gemini_session does not false-positive on paths with '.gemini' as substring."""
        # Path that contains .gemini but not as a directory component
        with patch.dict(
            os.environ,
            {"AOPS_SESSION_STATE_DIR": "/home/user/my.gemini-project/sessions/"},
        ):
            result = session_paths._is_gemini_session(
                "07328230-44d4-414b-9fec-191a6eec0948",
                {},
            )
            self.assertFalse(result, "Should not false-positive on .gemini as filename prefix")

    @patch.dict(
        os.environ,
        {"AOPS_SESSION_STATE_DIR": "/home/user/.gemini/tmp/abc123hash/"},
        clear=True,
    )
    def test_get_gate_file_path_gemini_state_dir_fallback(self):
        """get_gate_file_path returns a valid path for Gemini sessions detected via AOPS_SESSION_STATE_DIR.

        Integration regression test for GH#467: verifies that _is_gemini_session returning True
        via AOPS_SESSION_STATE_DIR does not cause ValueError in get_gate_file_path when
        transcript_path is absent from input_data (polecat worker scenario).
        """
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir) / ".gemini" / "tmp" / "abc123hash"
            state_dir.mkdir(parents=True, exist_ok=True)

            with patch.dict(
                os.environ,
                {"AOPS_SESSION_STATE_DIR": str(state_dir) + "/"},
            ):
                try:
                    gate_path = session_paths.get_gate_file_path(
                        "hydration",
                        "07328230-44d4-414b-9fec-191a6eec0948",
                        {},  # No transcript_path - simulating polecat worker
                    )
                except ValueError as exc:
                    self.fail(
                        f"get_gate_file_path raised ValueError unexpectedly for polecat worker: {exc}"
                    )

                self.assertIsNotNone(gate_path, "get_gate_file_path should return a path")
                self.assertIsInstance(gate_path, Path, "Expected Path object")
                self.assertIn("hydration", str(gate_path), "Gate name should appear in path")
                self.assertIn(".gemini", str(gate_path), "Path should be in Gemini directory")

    def test_get_gate_file_path_claude(self):
        """get_gate_file_path returns a valid path for Claude sessions."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, "home", return_value=Path(tmpdir)):
                # Mock get_claude_project_folder to avoid needing real cwd
                with patch("lib.session_paths.get_claude_project_folder", return_value="-project"):
                    gate_path = session_paths.get_gate_file_path(
                        "hydration", "07328230-44d4-414b-9fec-191a6eec0948", date="2026-01-24"
                    )

                    self.assertIn(".claude/projects/-project", str(gate_path))
                    self.assertIn("20260124-07328230-hydration.md", str(gate_path))

    def test_get_gate_file_path_gemini_prefix(self):
        """get_gate_file_path returns a valid path for Gemini sessions via prefix."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            # For Gemini, we need a logs dir
            project_hash = hashlib.sha256(b"test").hexdigest()
            gemini_base = Path(tmpdir) / ".gemini" / "tmp" / project_hash

            with (
                patch.object(Path, "home", return_value=Path(tmpdir)),
                patch.dict(
                    os.environ,
                    {"GEMINI_PROJECT_DIR": "test", "AOPS_SESSION_STATE_DIR": str(gemini_base)},
                ),
            ):
                gate_path = session_paths.get_gate_file_path(
                    "hydration", "gemini-2026-01-24-abc12345", date="2026-01-24"
                )

                self.assertIn(".gemini/tmp", str(gate_path))
                # gemini-20... doesn't match alphanumeric prefix, so it uses hash fallback for short hash
                expected_hash = hashlib.sha256(b"gemini-2026-01-24-abc12345").hexdigest()[:8]
                self.assertIn(f"20260124-{expected_hash}-hydration.md", str(gate_path))

    def test_get_gate_file_path_gemini_polecat(self):
        """get_gate_file_path returns a valid path for Gemini sessions (polecat style - UUID ID)."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir) / ".gemini" / "tmp" / "abc123hash"
            state_dir.mkdir(parents=True, exist_ok=True)

            with (
                patch.object(Path, "home", return_value=Path(tmpdir)),
                patch.dict(os.environ, {"AOPS_SESSION_STATE_DIR": str(state_dir)}),
            ):
                gate_path = session_paths.get_gate_file_path(
                    "hydration", "07328230-44d4-414b-9fec-191a6eec0948", date="2026-01-24"
                )

                self.assertIn(".gemini/tmp/abc123hash", str(gate_path))
                self.assertIn("logs/20260124-07328230-hydration.md", str(gate_path))


if __name__ == "__main__":
    unittest.main()
