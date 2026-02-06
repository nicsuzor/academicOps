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
HOOK_SCRIPT = (
    Path(__file__).parent.parent.parent / "aops-core" / "hooks" / "session_env_setup.sh"
)


class TestSessionEnvSetup:
    """Test environment setup logic."""

    def test_pythonpath_derived_from_script_loc(self, tmp_path: Path) -> None:
        """Script should derive local aops-core path and export PYTHONPATH."""
        # Create mock structure
        # hooks/session_env_setup.sh
        # lib/hook_utils.py

        # We use the real script, but we need to ensure it finds lib/hook_utils.py relative to it
        # Since we run the real script in-place, it points to real aops-core.

        env_file = tmp_path / "claude_env"
        env_file.touch()

        env = {
            k: v for k, v in os.environ.items() if k not in ("AOPS", "CLAUDE_ENV_FILE")
        }
        env["CLAUDE_ENV_FILE"] = str(env_file)

        result = subprocess.run(
            ["bash", str(HOOK_SCRIPT)],
            capture_output=True,
            text=True,
            env=env,
        )

        assert result.returncode == 0
        env_content = env_file.read_text()

        # Verify PYTHONPATH export
        # Should contain "aops-core" path
        assert "export PYTHONPATH=" in env_content
        assert "/aops-core" in env_content

        # Verify AOPS is NOT exported
        assert "export AOPS=" not in env_content



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
        assert os.access(HOOK_SCRIPT, os.X_OK), (
            f"Hook script not executable: {HOOK_SCRIPT}"
        )

    def test_script_has_shebang(self) -> None:
        """Hook script must have bash shebang."""
        content = HOOK_SCRIPT.read_text()
        assert content.startswith("#!/bin/bash"), "Script must have bash shebang"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
