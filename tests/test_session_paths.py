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
    def test_get_session_status_dir_gemini_raises_without_state_dir(self):
        """Gemini detected via session_id prefix only (no env var, no transcript) → fail fast.

        ``gemini-`` prefix alone is informational; without GEMINI_SESSION_ID we
        can't trust the cwd hash because the hook may be running outside the
        Gemini CLI process.
        """
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "project"
            project_root.mkdir(parents=True, exist_ok=True)

            with (
                patch.object(Path, "home", return_value=Path(tmpdir)),
                patch.object(Path, "cwd", return_value=project_root),
            ):
                # gemini- prefix triggers detection, but no transcript_path or
                # AOPS_SESSION_STATE_DIR means we can't determine the status dir
                with self.assertRaises(ValueError, msg="Gemini session detected"):
                    session_paths.get_session_status_dir("gemini-test-session")

    def test_get_session_status_dir_gemini_derives_from_cwd(self):
        """SessionStart with GEMINI_SESSION_ID set but no transcript_path → derive from cwd basename.

        Recent Gemini CLI versions name per-project tmp dirs as
        ``~/.gemini/tmp/<basename(cwd)>/``, not by sha256(cwd). Earlier we
        used sha256 here, which polluted ``~/.gemini/tmp/`` with orphan dirs
        and split session artefacts across two locations.
        """
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir) / "project"
            project_root.mkdir(parents=True, exist_ok=True)
            expected = Path(tmpdir) / ".gemini" / "tmp" / "project"

            with patch.dict(
                os.environ,
                {"GEMINI_SESSION_ID": "session-x", "PWD": str(project_root)},
                clear=True,
            ):
                with patch.object(Path, "home", return_value=Path(tmpdir)):
                    result = session_paths.get_session_status_dir(
                        "07328230-44d4-414b-9fec-191a6eec0948"
                    )
                    self.assertEqual(result, expected)

    def test_get_session_status_dir_gemini_prefers_pwd_over_getcwd(self):
        """The ``uv --directory`` wrapper chdir's into the extension dir, so
        ``os.getcwd()`` lies. PWD still reflects the user's project — use it
        when computing the workspace dir basename.
        """
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            user_project = Path(tmpdir) / "user_project"
            user_project.mkdir(parents=True, exist_ok=True)
            extension_dir = Path(tmpdir) / "extension_dir"
            extension_dir.mkdir(parents=True, exist_ok=True)

            with patch.dict(
                os.environ,
                {"GEMINI_SESSION_ID": "session-y", "PWD": str(user_project)},
                clear=True,
            ):
                with (
                    patch.object(Path, "home", return_value=Path(tmpdir)),
                    patch("os.getcwd", return_value=str(extension_dir)),
                ):
                    result = session_paths.get_session_status_dir("any-session-id")
                    # Workspace name comes from PWD, not the lying os.getcwd()
                    self.assertEqual(result.name, "user_project")

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
                # Pass a real UUID session_id to trigger the claude path
                # (NO FALLBACKS: only a UUID-shaped id, or explicit --client
                # claude, routes to ~/.claude — a non-UUID id now raises).
                result = session_paths.get_session_status_dir(
                    "07328230-44d4-414b-9fec-191a6eec0948"
                )
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
                result = session_paths.get_session_status_dir(
                    "07328230-44d4-414b-9fec-191a6eec0948", transcript_path=transcript_path
                )
                # Should detect Gemini from transcript_path and return gemini_base
                self.assertEqual(result, gemini_base)

    def test_is_gemini_session_transcript_path(self):
        """_is_gemini_session detects Gemini via transcript_path."""
        # UUID session_id (no gemini- prefix) with Gemini transcript_path
        result = session_paths._is_gemini_session(
            "07328230-44d4-414b-9fec-191a6eec0948",
            transcript_path="/home/user/.gemini/tmp/hash/chats/session.json",
        )
        self.assertTrue(result)

    @patch.dict(os.environ, {"USER": "worker"}, clear=True)
    def test_is_gemini_session_prefix_not_detected(self):
        """NO FALLBACKS: a 'gemini-' session-id prefix is no longer a detection
        signal. Without GEMINI_SESSION_ID / a /.gemini/ transcript_path, it is
        NOT treated as Gemini here (the explicit --client signal routes it)."""
        result = session_paths._is_gemini_session("gemini-2026-01-01-abc123", None)
        self.assertFalse(result)

    @patch.dict(os.environ, {"GEMINI_SESSION_ID": "test-session-id"})
    def test_is_gemini_session_env_var(self):
        """_is_gemini_session detects Gemini via GEMINI_SESSION_ID env var."""
        result = session_paths._is_gemini_session(None, None)
        self.assertTrue(result)

    @patch.dict(os.environ, {}, clear=True)
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
    def test_is_gemini_session_state_dir_not_detected(self):
        """NO FALLBACKS: AOPS_SESSION_STATE_DIR is no longer a _is_gemini_session
        signal — get_session_status_dir consumes it directly (step 1), so a
        '/.gemini/' state dir does NOT make _is_gemini_session return True.
        Supersedes the GH#467 fallback, which silently mis-routed sessions.
        """
        # UUID session_id, no transcript_path; the gemini state dir is set in env
        # but is irrelevant to detection now.
        result = session_paths._is_gemini_session(
            "07328230-44d4-414b-9fec-191a6eec0948",
            {},  # No transcript_path
        )
        self.assertFalse(result, "state dir alone must not trigger Gemini detection")

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
                        "enforcer",
                        "07328230-44d4-414b-9fec-191a6eec0948",
                        {},  # No transcript_path - simulating polecat worker
                    )
                except ValueError as exc:
                    self.fail(
                        f"get_gate_file_path raised ValueError unexpectedly for polecat worker: {exc}"
                    )

                self.assertIsNotNone(gate_path, "get_gate_file_path should return a path")
                self.assertIsInstance(gate_path, Path, "Expected Path object")
                self.assertIn("enforcer", str(gate_path), "Gate name should appear in path")
                self.assertIn(".gemini", str(gate_path), "Path should be in Gemini directory")

    def test_get_gate_file_path_claude(self):
        """get_gate_file_path returns a valid path for Claude sessions."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(Path, "home", return_value=Path(tmpdir)):
                # Mock get_claude_project_folder to avoid needing real cwd
                with patch("lib.session_paths.get_claude_project_folder", return_value="-project"):
                    # Clear env vars that leak from live sessions
                    with patch.dict(os.environ, {}, clear=False):
                        os.environ.pop("AOPS_GATE_FILE_ENFORCER", None)
                        os.environ.pop("AOPS_SESSIONS", None)
                        os.environ.pop("GEMINI_SESSION_ID", None)
                        os.environ.pop("AOPS_SESSION_STATE_DIR", None)
                        # Pop the container marker too: when set (=1, e.g. the
                        # suite runs inside a polecat container) get_gate_file_path
                        # routes to the container state dir, not .claude/projects,
                        # breaking the assertion below. This env leak was the
                        # cause of the intermittent test_get_gate_file_path_claude
                        # failure flagged during the agy-hook consolidation.
                        os.environ.pop("AOPS_POLECAT_CONTAINER", None)
                        gate_path = session_paths.get_gate_file_path(
                            "enforcer", "07328230-44d4-414b-9fec-191a6eec0948", date="2026-01-24"
                        )

                        self.assertIn(".claude/projects/-project", str(gate_path))
                        # Use regex to match YYYYMMDD-HH-shorthash-gate.md
                        import re

                        self.assertTrue(
                            re.search(r"20260124-\d{4}-07328230-.*-enforcer\.md", str(gate_path))
                        )

    def test_get_gate_file_path_gemini_prefix(self):
        """get_gate_file_path returns a valid path for Gemini sessions via prefix."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            # For Gemini, we need a logs dir
            project_hash = hashlib.sha256(b"test").hexdigest()
            gemini_base = Path(tmpdir) / ".gemini" / "tmp" / project_hash

            env_overrides = {
                "GEMINI_PROJECT_DIR": "test",
                "AOPS_SESSION_STATE_DIR": str(gemini_base),
            }
            with (
                patch.object(Path, "home", return_value=Path(tmpdir)),
                patch.dict(os.environ, env_overrides, clear=False),
            ):
                os.environ.pop("AOPS_GATE_FILE_ENFORCER", None)
                os.environ.pop("AOPS_SESSIONS", None)
                gate_path = session_paths.get_gate_file_path(
                    "enforcer", "gemini-2026-01-24-abc12345", date="2026-01-24"
                )

                self.assertIn(".gemini/tmp", str(gate_path))
                # gemini-20... doesn't match alphanumeric prefix, so it uses hash fallback for short hash
                expected_hash = hashlib.sha256(b"gemini-2026-01-24-abc12345").hexdigest()[:8]
                import re

                self.assertTrue(
                    re.search(rf"20260124-\d{{4}}-{expected_hash}-.*-enforcer\.md", str(gate_path))
                )

    def test_get_gate_file_path_gemini_polecat(self):
        """get_gate_file_path returns a valid path for Gemini sessions (polecat style - UUID ID).

        Gate context files share the session status dir with state and hooks —
        no ``logs/`` subdir split.
        """
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir) / ".gemini" / "tmp" / "abc123hash"
            state_dir.mkdir(parents=True, exist_ok=True)

            with (
                patch.object(Path, "home", return_value=Path(tmpdir)),
                patch.dict(os.environ, {"AOPS_SESSION_STATE_DIR": str(state_dir)}, clear=False),
            ):
                os.environ.pop("AOPS_GATE_FILE_ENFORCER", None)
                os.environ.pop("AOPS_SESSIONS", None)
                gate_path = session_paths.get_gate_file_path(
                    "enforcer", "07328230-44d4-414b-9fec-191a6eec0948", date="2026-01-24"
                )

                self.assertIn(".gemini/tmp/abc123hash", str(gate_path))
                self.assertEqual(gate_path.parent, state_dir)
                import re

                self.assertTrue(
                    re.search(r"20260124-\d{4}-07328230-.*-enforcer\.md", gate_path.name)
                )


if __name__ == "__main__":
    unittest.main()
