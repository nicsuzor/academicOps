"""E2E: verify Gemini CLI fires our extension hooks.

Gemini fires lifecycle hooks (SessionStart, SessionEnd) before auth
completes, so we can test with a dummy API key — no real credentials
needed. The assertion: did our hook log get written with a SessionStart
entry? If yes, the entire chain worked end-to-end through Gemini CLI.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.integration
class TestGeminiHooksFire:
    """End-to-end: Gemini CLI fires our extension hooks."""

    @pytest.fixture(scope="class")
    def gemini_session(self, tmp_path_factory):
        """Run Gemini CLI with dummy auth, return hook log entries and stderr."""
        if not shutil.which("gemini"):
            pytest.skip("gemini CLI not in PATH")

        # Verify extension is installed with Gemini-format hooks
        ext_dir = Path.home() / ".gemini" / "extensions" / "aops-core"
        if not ext_dir.exists():
            pytest.skip("aops-core extension not installed")
        hooks_json = ext_dir / "hooks" / "hooks.json"
        if not hooks_json.exists():
            pytest.skip(
                "aops-core extension has no hooks/hooks.json — "
                "installed from repo root instead of dist/aops-gemini?"
            )

        tmp_path = tmp_path_factory.mktemp("gemini_hooks")
        sessions_dir = tmp_path / "hook-sessions"
        sessions_dir.mkdir()

        env = os.environ.copy()
        env["GEMINI_API_KEY"] = "dummy-no-auth-needed-for-hook-test"
        env["AOPS_SESSIONS"] = str(sessions_dir)
        env["AOPS"] = str(REPO_ROOT)
        env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT / "aops-core")
        env.pop("NTFY_TOPIC", None)

        result = subprocess.run(
            ["gemini", "-p", "test"],
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
            cwd=tmp_path,
        )

        # Parse hook log entries
        entries = []
        for log_file in sessions_dir.rglob("*-hooks.jsonl"):
            for line in log_file.read_text().splitlines():
                if line.strip():
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass

        return {
            "entries": entries,
            "events": [e.get("hook_event") for e in entries],
            "stderr": result.stderr,
            "stdout": result.stdout,
            "returncode": result.returncode,
            "sessions_dir": sessions_dir,
        }

    def test_session_start_hook_fires(self, gemini_session):
        """Gemini must fire our SessionStart hook and produce a log entry."""
        assert "SessionStart" in gemini_session["events"], (
            f"SessionStart hook did not fire through Gemini CLI.\n"
            f"Events logged: {gemini_session['events']}\n"
            f"Hook logs: {list(gemini_session['sessions_dir'].rglob('*.jsonl'))}\n"
            f"stderr (last 500): {gemini_session['stderr'][-500:]}\n"
            f"stdout (last 200): {gemini_session['stdout'][-200:]}"
        )

    def test_hook_log_has_session_id(self, gemini_session):
        """Hook log entries must have a session ID assigned by the router."""
        starts = [e for e in gemini_session["entries"] if e.get("hook_event") == "SessionStart"]
        if not starts:
            pytest.skip("SessionStart didn't fire")
        session_id = starts[0].get("session_id", "")
        assert session_id and session_id != "unknown", (
            f"SessionStart entry has no valid session_id: {starts[0]}"
        )

    def test_hook_output_has_decision(self, gemini_session):
        """Hook output must contain a verdict that Gemini can act on."""
        starts = [e for e in gemini_session["entries"] if e.get("hook_event") == "SessionStart"]
        if not starts:
            pytest.skip("SessionStart didn't fire")
        output = starts[0].get("output", {})
        assert output.get("verdict") in ("allow", "deny"), (
            f"SessionStart output missing valid verdict: {output}"
        )


@pytest.mark.integration
class TestGeminiHooksWithSettings:
    """Verify hooks still fire when settings.json exists.

    Regression test for the polecat/crew bug: writing a settings.json
    with security.auth.selectedType caused Gemini to exit before hooks
    fired. This test proves hooks survive a settings.json.
    """

    @pytest.fixture(scope="class")
    def gemini_session_with_settings(self, tmp_path_factory):
        """Run Gemini with a GEMINI_CLI_HOME that has a settings.json."""
        if not shutil.which("gemini"):
            pytest.skip("gemini CLI not in PATH")

        ext_dir = Path.home() / ".gemini" / "extensions" / "aops-core"
        if not ext_dir.exists():
            pytest.skip("aops-core extension not installed")
        hooks_json = ext_dir / "hooks" / "hooks.json"
        if not hooks_json.exists():
            pytest.skip(
                "aops-core extension has no hooks/hooks.json — "
                "installed from repo root instead of dist/aops-gemini?"
            )

        tmp_path = tmp_path_factory.mktemp("gemini_settings")
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()

        # Simulate polecat crew: custom GEMINI_CLI_HOME with settings + extensions
        gemini_home = tmp_path / "gemini-home"
        gemini_home.mkdir()
        dot_gemini = gemini_home / ".gemini"
        dot_gemini.mkdir()

        # Copy extensions from system install
        shutil.copytree(
            Path.home() / ".gemini" / "extensions",
            dot_gemini / "extensions",
        )

        # Copy state files Gemini CLI needs for project registry
        for f in (
            "extension_integrity.json",
            "projects.json",
            "gemini-credentials.json",
            "state.json",
        ):
            src = Path.home() / ".gemini" / f
            if src.exists():
                shutil.copy2(src, dot_gemini / f)

        # Write the polecat template settings (the thing that used to break hooks)
        template = REPO_ROOT / "polecat" / "defaults" / "gemini-settings.json"
        shutil.copy2(template, dot_gemini / "settings.json")

        env = os.environ.copy()
        env["GEMINI_API_KEY"] = "dummy-no-auth-needed"
        env["GEMINI_CLI_HOME"] = str(gemini_home)
        env["AOPS_SESSIONS"] = str(sessions_dir)
        env["AOPS"] = str(REPO_ROOT)
        env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT / "aops-core")
        env.pop("NTFY_TOPIC", None)

        result = subprocess.run(
            ["gemini", "-p", "test"],
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
            cwd=tmp_path,
        )

        entries = []
        for log_file in sessions_dir.rglob("*-hooks.jsonl"):
            for line in log_file.read_text().splitlines():
                if line.strip():
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass

        return {
            "entries": entries,
            "events": [e.get("hook_event") for e in entries],
            "stderr": result.stderr,
            "stdout": result.stdout,
            "settings_json": (dot_gemini / "settings.json").read_text(),
        }

    def test_hooks_fire_with_polecat_settings(self, gemini_session_with_settings):
        """Hooks must fire even with the polecat settings.json template.

        This is the exact regression that caused the original bug: polecat
        wrote a settings.json with selectedType, Gemini exited on auth
        mismatch before hooks fired.
        """
        sess = gemini_session_with_settings
        assert "SessionStart" in sess["events"], (
            f"Hooks did not fire with polecat settings template.\n"
            f"settings.json: {sess['settings_json']}\n"
            f"stderr (last 500): {sess['stderr'][-500:]}\n"
            f"stdout (last 200): {sess['stdout'][-200:]}"
        )
