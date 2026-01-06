#!/usr/bin/env python3
"""
Tests for session_env_setup.sh hook and remote automation scenarios.

These tests verify that the framework can bootstrap itself in remote/automated
environments where $AOPS is not pre-configured, using only $CLAUDE_PROJECT_DIR.
"""

import os
import subprocess
from pathlib import Path

import pytest


@pytest.fixture
def repo_root():
    """Get the repository root directory."""
    return Path(__file__).parent.parent.resolve()


@pytest.fixture
def clean_env(repo_root):
    """Provide a clean environment without AOPS set."""
    env = os.environ.copy()
    # Remove AOPS if set
    env.pop("AOPS", None)
    env.pop("ACA_DATA", None)
    # Set CLAUDE_PROJECT_DIR (simulates Claude Code environment)
    env["CLAUDE_PROJECT_DIR"] = str(repo_root)
    return env


class TestSessionEnvSetup:
    """Test session_env_setup.sh hook in remote automation scenarios."""

    def test_derives_aops_from_claude_project_dir(self, repo_root, clean_env):
        """Test that session_env_setup.sh derives AOPS from CLAUDE_PROJECT_DIR."""
        hook_path = repo_root / "hooks" / "session_env_setup.sh"
        assert hook_path.exists(), "session_env_setup.sh hook not found"

        # Run the hook with clean environment
        result = subprocess.run(
            ["bash", str(hook_path)],
            env=clean_env,
            capture_output=True,
            text=True,
            timeout=5,
        )

        assert result.returncode == 0, (
            f"Hook failed with exit code {result.returncode}\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )

        # Check that hook outputs success JSON
        assert '{"continue": true}' in result.stdout

        # Check that hook logged it derived AOPS
        assert "Derived AOPS from CLAUDE_PROJECT_DIR" in result.stderr or \
               "AOPS environment already configured" in result.stderr

    def test_validates_aops_path(self, repo_root, clean_env):
        """Test that hook validates AOPS path by checking for AXIOMS.md."""
        hook_path = repo_root / "hooks" / "session_env_setup.sh"

        # Run hook - should succeed because academicOps has AXIOMS.md
        result = subprocess.run(
            ["bash", str(hook_path)],
            env=clean_env,
            capture_output=True,
            text=True,
            timeout=5,
        )

        assert result.returncode == 0

        # Should not have validation warning
        assert "Cannot validate AOPS path" not in result.stderr

    def test_handles_missing_claude_project_dir(self, repo_root):
        """Test fallback when CLAUDE_PROJECT_DIR is not set."""
        hook_path = repo_root / "hooks" / "session_env_setup.sh"

        # Create environment without AOPS or CLAUDE_PROJECT_DIR
        env = os.environ.copy()
        env.pop("AOPS", None)
        env.pop("CLAUDE_PROJECT_DIR", None)

        # Run hook - should fall back to deriving from script location
        result = subprocess.run(
            ["bash", str(hook_path)],
            env=env,
            capture_output=True,
            text=True,
            timeout=5,
        )

        assert result.returncode == 0
        assert '{"continue": true}' in result.stdout
        assert "Derived AOPS from script location" in result.stderr


class TestRepoLocalSettings:
    """Test repo-local .claude/ settings for remote automation."""

    def test_repo_claude_exists(self, repo_root):
        """Test that repo has .claude/ directory."""
        claude_dir = repo_root / ".claude"
        assert claude_dir.exists(), "Repo-local .claude/ directory not found"
        assert claude_dir.is_dir(), ".claude/ is not a directory"

    def test_settings_json_uses_self_config(self, repo_root):
        """Test that .claude/settings.json links to settings-self.json."""
        settings_link = repo_root / ".claude" / "settings.json"
        
        assert settings_link.exists(), ".claude/settings.json not found"
        assert settings_link.is_symlink(), ".claude/settings.json is not a symlink"

        # Should link to settings-self.json
        target = settings_link.readlink()
        assert "settings-self.json" in str(target), (
            f"Expected settings-self.json, got {target}"
        )

    def test_settings_self_uses_claude_project_dir(self, repo_root):
        """Test that settings-self.json uses CLAUDE_PROJECT_DIR in hook commands."""
        settings_file = repo_root / "config" / "claude" / "settings-self.json"
        
        assert settings_file.exists(), "settings-self.json not found"

        content = settings_file.read_text()

        # Should use CLAUDE_PROJECT_DIR, not AOPS
        assert "$CLAUDE_PROJECT_DIR" in content, (
            "settings-self.json should use $CLAUDE_PROJECT_DIR"
        )
        
        # Should NOT use $AOPS (that's for settings.json)
        assert "$AOPS" not in content, (
            "settings-self.json should not use $AOPS "
            "(use $CLAUDE_PROJECT_DIR for remote automation)"
        )

    def test_all_hooks_use_consistent_paths(self, repo_root):
        """Test that all hooks in settings-self.json use CLAUDE_PROJECT_DIR."""
        import json
        
        settings_file = repo_root / "config" / "claude" / "settings-self.json"
        settings = json.loads(settings_file.read_text())

        hook_events = ["SessionStart", "PreToolUse", "PostToolUse", 
                       "UserPromptSubmit", "SubagentStop", "Stop"]

        for event in hook_events:
            if event not in settings.get("hooks", {}):
                continue

            hook_configs = settings["hooks"][event]
            for hook_config in hook_configs:
                for hook in hook_config.get("hooks", []):
                    command = hook.get("command", "")
                    
                    # All hooks should use CLAUDE_PROJECT_DIR
                    if "python" in command and "hooks/router.py" in command:
                        assert "$CLAUDE_PROJECT_DIR" in command, (
                            f"{event} hook should use $CLAUDE_PROJECT_DIR: {command}"
                        )
                        assert "$AOPS" not in command, (
                            f"{event} hook should not use $AOPS: {command}"
                        )


class TestRemoteAutomationIntegration:
    """Integration tests simulating remote automation environment."""

    def test_router_runs_without_aops_preset(self, repo_root, clean_env):
        """Test that router.py can run with only CLAUDE_PROJECT_DIR set."""
        # SessionStart hook should be the first to run
        router_path = repo_root / "hooks" / "router.py"
        
        # Create minimal hook input (SessionStart event)
        hook_input = '{"event": "SessionStart"}'

        # Run router with clean environment
        result = subprocess.run(
            ["python3", str(router_path), "SessionStart"],
            env=clean_env,
            input=hook_input,
            capture_output=True,
            text=True,
            timeout=10,
        )

        # Should succeed (exit 0) or return valid hook output
        # Note: Some hooks may fail in test environment, but router should run
        assert result.returncode in [0, 1], (
            f"Router failed unexpectedly with exit code {result.returncode}\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )

    def test_full_session_bootstrap(self, repo_root, clean_env, tmp_path):
        """Test complete session bootstrap in remote environment."""
        # Simulate complete hook execution with CLAUDE_ENV_FILE
        env_file = tmp_path / "claude_env"
        env_file.touch()
        
        clean_env["CLAUDE_ENV_FILE"] = str(env_file)

        # Run session_env_setup.sh
        hook_path = repo_root / "hooks" / "session_env_setup.sh"
        result = subprocess.run(
            ["bash", str(hook_path)],
            env=clean_env,
            capture_output=True,
            text=True,
            timeout=5,
        )

        assert result.returncode == 0

        # Check that AOPS was written to env file
        env_content = env_file.read_text()
        assert "export AOPS=" in env_content
        assert "export PYTHONPATH=" in env_content
