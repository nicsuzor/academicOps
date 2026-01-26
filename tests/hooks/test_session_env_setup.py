#!/usr/bin/env python3
"""Tests for session_env_setup.sh hook.

Tests environment variable setup logic for SessionStart hook:
- AOPS already set scenario
- AOPS derived from CLAUDE_PROJECT_DIR
- AOPS derived from script location (fallback)
- PYTHONPATH addition to CLAUDE_ENV_FILE
"""

import os
import subprocess
import tempfile
from pathlib import Path

import pytest

# Path to the hook script
HOOK_SCRIPT = Path(__file__).parent.parent.parent / "hooks" / "session_env_setup.sh"


class TestAOPSAlreadySet:
    """Test behavior when AOPS is already set in environment."""

    def test_aops_already_set_and_valid(self, tmp_path: Path) -> None:
        """When AOPS is already set and directory exists, script should use it."""
        # Create a mock AOPS directory with required file
        mock_aops = tmp_path / "mock_aops"
        mock_aops.mkdir()
        (mock_aops / "AXIOMS.md").touch()

        result = subprocess.run(
            ["bash", str(HOOK_SCRIPT)],
            capture_output=True,
            text=True,
            env={**os.environ, "AOPS": str(mock_aops)},
        )

        assert result.returncode == 0
        assert '{"continue": true}' in result.stdout
        assert "AOPS environment already configured" in result.stderr
        assert str(mock_aops) in result.stderr

    def test_aops_set_but_directory_missing(self, tmp_path: Path) -> None:
        """When AOPS is set but directory doesn't exist, should derive new path."""
        nonexistent = tmp_path / "nonexistent"

        # Need to provide CLAUDE_PROJECT_DIR as fallback
        mock_project = tmp_path / "project"
        mock_project.mkdir()
        (mock_project / "AXIOMS.md").touch()

        result = subprocess.run(
            ["bash", str(HOOK_SCRIPT)],
            capture_output=True,
            text=True,
            env={
                **os.environ,
                "AOPS": str(nonexistent),
                "CLAUDE_PROJECT_DIR": str(mock_project),
            },
        )

        assert result.returncode == 0
        # Should derive from CLAUDE_PROJECT_DIR since AOPS dir doesn't exist
        assert "AOPS set to:" in result.stderr


class TestDeriveFromClaudeProjectDir:
    """Test AOPS derivation from CLAUDE_PROJECT_DIR."""

    def test_derive_from_claude_project_dir(self, tmp_path: Path) -> None:
        """When AOPS not set, should derive from CLAUDE_PROJECT_DIR."""
        mock_project = tmp_path / "project"
        mock_project.mkdir()
        (mock_project / "AXIOMS.md").touch()

        # Clear AOPS from env
        env = {k: v for k, v in os.environ.items() if k != "AOPS"}
        env["CLAUDE_PROJECT_DIR"] = str(mock_project)

        result = subprocess.run(
            ["bash", str(HOOK_SCRIPT)],
            capture_output=True,
            text=True,
            env=env,
        )

        assert result.returncode == 0
        assert '{"continue": true}' in result.stdout
        assert "AOPS set to:" in result.stderr
        assert str(mock_project) in result.stderr

    def test_warning_when_axioms_md_missing(self, tmp_path: Path) -> None:
        """When AXIOMS.md not found at derived path, should warn but continue."""
        mock_project = tmp_path / "project"
        mock_project.mkdir()
        # Intentionally NOT creating AXIOMS.md

        env = {k: v for k, v in os.environ.items() if k != "AOPS"}
        env["CLAUDE_PROJECT_DIR"] = str(mock_project)

        result = subprocess.run(
            ["bash", str(HOOK_SCRIPT)],
            capture_output=True,
            text=True,
            env=env,
        )

        assert result.returncode == 0
        assert '{"continue": true}' in result.stdout
        assert "WARNING: Cannot validate AOPS path" in result.stderr


class TestDeriveFromScriptLocation:
    """Test AOPS derivation from script location (fallback)."""

    def test_fallback_to_script_location(self) -> None:
        """When neither AOPS nor CLAUDE_PROJECT_DIR set, derive from script location."""
        # Clear both env vars
        env = {k: v for k, v in os.environ.items() if k not in ("AOPS", "CLAUDE_PROJECT_DIR")}

        result = subprocess.run(
            ["bash", str(HOOK_SCRIPT)],
            capture_output=True,
            text=True,
            env=env,
        )

        assert result.returncode == 0
        assert '{"continue": true}' in result.stdout
        # Script should derive AOPS from its own location (hooks/../ = aops-core)
        assert "AOPS set to:" in result.stderr


class TestClaudeEnvFile:
    """Test writing to CLAUDE_ENV_FILE."""

    def test_writes_aops_to_env_file(self, tmp_path: Path) -> None:
        """When CLAUDE_ENV_FILE is set, should write AOPS export to it."""
        env_file = tmp_path / "claude_env"
        env_file.touch()

        mock_project = tmp_path / "project"
        mock_project.mkdir()
        (mock_project / "AXIOMS.md").touch()

        env = {k: v for k, v in os.environ.items() if k != "AOPS"}
        env["CLAUDE_PROJECT_DIR"] = str(mock_project)
        env["CLAUDE_ENV_FILE"] = str(env_file)

        result = subprocess.run(
            ["bash", str(HOOK_SCRIPT)],
            capture_output=True,
            text=True,
            env=env,
        )

        assert result.returncode == 0
        env_content = env_file.read_text()
        assert f'export AOPS="{mock_project}"' in env_content
        assert "Environment variables written to CLAUDE_ENV_FILE" in result.stderr

    def test_writes_pythonpath_to_env_file(self, tmp_path: Path) -> None:
        """When CLAUDE_ENV_FILE is set, should write PYTHONPATH export to it."""
        env_file = tmp_path / "claude_env"
        env_file.touch()

        mock_project = tmp_path / "project"
        mock_project.mkdir()
        (mock_project / "AXIOMS.md").touch()

        env = {k: v for k, v in os.environ.items() if k != "AOPS"}
        env["CLAUDE_PROJECT_DIR"] = str(mock_project)
        env["CLAUDE_ENV_FILE"] = str(env_file)

        result = subprocess.run(
            ["bash", str(HOOK_SCRIPT)],
            capture_output=True,
            text=True,
            env=env,
        )

        assert result.returncode == 0
        env_content = env_file.read_text()
        assert "export PYTHONPATH=" in env_content
        assert str(mock_project) in env_content

    def test_no_duplicate_writes_to_env_file(self, tmp_path: Path) -> None:
        """Should not duplicate AOPS in CLAUDE_ENV_FILE if already present."""
        env_file = tmp_path / "claude_env"

        mock_project = tmp_path / "project"
        mock_project.mkdir()
        (mock_project / "AXIOMS.md").touch()

        # Pre-populate env file with AOPS
        env_file.write_text(f'export AOPS="{mock_project}"\nexport PYTHONPATH="{mock_project}:$PYTHONPATH"\n')

        env = {k: v for k, v in os.environ.items() if k != "AOPS"}
        env["CLAUDE_PROJECT_DIR"] = str(mock_project)
        env["CLAUDE_ENV_FILE"] = str(env_file)

        result = subprocess.run(
            ["bash", str(HOOK_SCRIPT)],
            capture_output=True,
            text=True,
            env=env,
        )

        assert result.returncode == 0
        env_content = env_file.read_text()
        # Should only have one AOPS export line
        assert env_content.count("export AOPS=") == 1

    def test_no_env_file_write_when_not_set(self, tmp_path: Path) -> None:
        """When CLAUDE_ENV_FILE not set, should not crash."""
        mock_project = tmp_path / "project"
        mock_project.mkdir()
        (mock_project / "AXIOMS.md").touch()

        env = {k: v for k, v in os.environ.items() if k not in ("AOPS", "CLAUDE_ENV_FILE")}
        env["CLAUDE_PROJECT_DIR"] = str(mock_project)

        result = subprocess.run(
            ["bash", str(HOOK_SCRIPT)],
            capture_output=True,
            text=True,
            env=env,
        )

        assert result.returncode == 0
        assert '{"continue": true}' in result.stdout


class TestJsonOutput:
    """Test JSON output format."""

    def test_outputs_continue_true_json(self, tmp_path: Path) -> None:
        """Hook should output {"continue": true} JSON to stdout."""
        mock_project = tmp_path / "project"
        mock_project.mkdir()
        (mock_project / "AXIOMS.md").touch()

        env = {k: v for k, v in os.environ.items() if k != "AOPS"}
        env["CLAUDE_PROJECT_DIR"] = str(mock_project)

        result = subprocess.run(
            ["bash", str(HOOK_SCRIPT)],
            capture_output=True,
            text=True,
            env=env,
        )

        assert result.returncode == 0
        # Output should be valid JSON on a single line
        import json

        stdout_lines = [line for line in result.stdout.strip().split("\n") if line]
        assert len(stdout_lines) == 1
        output = json.loads(stdout_lines[0])
        assert output == {"continue": True}


class TestScriptExecutability:
    """Test script file properties."""

    def test_script_exists(self) -> None:
        """Hook script file must exist."""
        assert HOOK_SCRIPT.exists(), f"Hook script not found: {HOOK_SCRIPT}"

    def test_script_is_executable(self) -> None:
        """Hook script must be executable."""
        assert os.access(HOOK_SCRIPT, os.X_OK), f"Hook script not executable: {HOOK_SCRIPT}"

    def test_script_has_shebang(self) -> None:
        """Hook script must have bash shebang."""
        content = HOOK_SCRIPT.read_text()
        assert content.startswith("#!/bin/bash"), "Script must have bash shebang"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
