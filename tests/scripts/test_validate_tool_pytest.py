#!/usr/bin/env python3
"""
Pytest tests for validate_tool.py

Tests the validation functionality using proper pytest framework with absolute paths.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest


# Get the working directory for constructing absolute paths
WORKING_DIR = Path("/home/nic/src/writing")
SCRIPT_PATH = WORKING_DIR / "bot/scripts/validate_tool.py"


def run_validation(tool_name: str, tool_input: dict) -> dict:
    """
    Run validation script and return parsed output.

    Returns:
        dict with keys: returncode, permission_decision, reason
    """
    input_data = {
        "tool_name": tool_name,
        "tool_input": tool_input
    }

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        input=json.dumps(input_data),
        capture_output=True,
        text=True
    )

    # Parse JSON output
    try:
        output = json.loads(result.stderr.strip())
        permission_decision = output.get("hookSpecificOutput", {}).get("permissionDecision", "unknown")
        reason = output.get("hookSpecificOutput", {}).get("permissionDecisionReason", "")
    except (json.JSONDecodeError, KeyError):
        permission_decision = "error"
        reason = result.stderr

    return {
        "returncode": result.returncode,
        "permission_decision": permission_decision,
        "reason": reason
    }


class TestMarkdownProhibition:
    """Test .md file creation prohibition with absolute paths."""

    def test_blocks_md_in_root(self):
        """Should block .md file creation in project root."""
        result = run_validation(
            "Write",
            {
                "file_path": str(WORKING_DIR / "README.md"),
                "content": "# Test",
                "subagent_type": "developer"
            }
        )
        assert result["returncode"] == 1
        assert result["permission_decision"] == "deny"
        assert "All code should be self-documenting" in result["reason"]

    def test_blocks_md_in_docs(self):
        """Should block .md file creation in docs/ directory."""
        result = run_validation(
            "Write",
            {
                "file_path": str(WORKING_DIR / "docs/guide.md"),
                "content": "# Guide",
                "subagent_type": "developer"
            }
        )
        assert result["returncode"] == 1
        assert result["permission_decision"] == "deny"

    def test_allows_md_in_papers(self):
        """Should allow .md file creation in papers/ directory."""
        result = run_validation(
            "Write",
            {
                "file_path": str(WORKING_DIR / "papers/research.md"),
                "content": "# Research",
                "subagent_type": "developer"
            }
        )
        assert result["returncode"] == 0
        assert result["permission_decision"] == "allow"

    def test_allows_md_in_manuscripts(self):
        """Should allow .md file creation in manuscripts/ directory."""
        result = run_validation(
            "Write",
            {
                "file_path": str(WORKING_DIR / "manuscripts/draft.md"),
                "content": "# Draft",
                "subagent_type": "developer"
            }
        )
        assert result["returncode"] == 0
        assert result["permission_decision"] == "allow"

    def test_allows_md_in_bot_agents(self):
        """Should allow .md file creation in bot/agents/ directory."""
        result = run_validation(
            "Write",
            {
                "file_path": str(WORKING_DIR / "bot/agents/test.md"),
                "content": "# Test Agent",
                "subagent_type": "developer"
            }
        )
        assert result["returncode"] == 0
        assert result["permission_decision"] == "allow"

    def test_allows_md_in_project_papers(self):
        """Should allow .md file creation in projects/*/papers/ directory."""
        result = run_validation(
            "Write",
            {
                "file_path": str(WORKING_DIR / "projects/myproject/papers/paper.md"),
                "content": "# Paper",
                "subagent_type": "developer"
            }
        )
        assert result["returncode"] == 0
        assert result["permission_decision"] == "allow"

    def test_allows_trainer_to_create_any_md(self):
        """Should allow trainer agent to create .md files anywhere."""
        result = run_validation(
            "Write",
            {
                "file_path": str(WORKING_DIR / "docs/trainer-created.md"),
                "content": "# Created by trainer",
                "subagent_type": "trainer"
            }
        )
        assert result["returncode"] == 0
        assert result["permission_decision"] == "allow"

    def test_blocks_md_outside_working_dir(self):
        """Should block .md file creation outside working directory."""
        result = run_validation(
            "Write",
            {
                "file_path": "/tmp/external.md",
                "content": "# External",
                "subagent_type": "developer"
            }
        )
        assert result["returncode"] == 1
        assert result["permission_decision"] == "deny"


class TestPythonInlineProhibition:
    """Test python -c inline execution prohibition."""

    def test_blocks_python_dash_c(self):
        """Should block python -c commands."""
        result = run_validation(
            "Bash",
            {
                "command": "python -c 'print(1+1)'",
                "subagent_type": "developer"
            }
        )
        assert result["returncode"] == 1
        assert result["permission_decision"] == "deny"
        assert "Inline Python execution" in result["reason"]
        assert "Create a proper test file" in result["reason"]

    def test_blocks_python3_dash_c(self):
        """Should block python3 -c commands."""
        result = run_validation(
            "Bash",
            {
                "command": "python3 -c 'import sys; print(sys.version)'",
                "subagent_type": "developer"
            }
        )
        assert result["returncode"] == 1
        assert result["permission_decision"] == "deny"

    def test_blocks_python_dash_c_for_trainer(self):
        """Should block python -c even for trainer agent (no exceptions)."""
        result = run_validation(
            "Bash",
            {
                "command": "python -c 'print(\"test\")'",
                "subagent_type": "trainer"
            }
        )
        assert result["returncode"] == 1
        assert result["permission_decision"] == "deny"
        assert "prohibited for all agents" in result["reason"]

    def test_blocks_python_dash_c_in_complex_command(self):
        """Should block python -c in complex command chains."""
        result = run_validation(
            "Bash",
            {
                "command": "cd /tmp && python -c 'import os; print(os.getcwd())'",
                "subagent_type": "developer"
            }
        )
        assert result["returncode"] == 1
        assert result["permission_decision"] == "deny"

    def test_allows_python_script_execution(self):
        """Should allow normal python script execution."""
        result = run_validation(
            "Bash",
            {
                "command": "uv run python test_script.py",
                "subagent_type": "developer"
            }
        )
        # This will be allowed (python -c is not present)
        # Note: May trigger uv run warning, but not blocked
        assert result["returncode"] == 0

    def test_allows_python_module_execution(self):
        """Should allow python -m module execution."""
        result = run_validation(
            "Bash",
            {
                "command": "uv run python -m pytest tests/",
                "subagent_type": "developer"
            }
        )
        # python -m is allowed, only python -c is blocked
        assert result["returncode"] == 0


class TestUvRunWarning:
    """Test uv run warning (should warn, not block)."""

    def test_warns_python_without_uv_run(self):
        """Should warn when using python without uv run."""
        result = run_validation(
            "Bash",
            {
                "command": "python script.py",
                "subagent_type": "developer"
            }
        )
        assert result["returncode"] == 0  # Warns but doesn't block
        assert result["permission_decision"] == "allow"
        assert "uv run" in result["reason"].lower()

    def test_no_warning_with_uv_run(self):
        """Should not warn when using uv run."""
        result = run_validation(
            "Bash",
            {
                "command": "uv run python script.py",
                "subagent_type": "developer"
            }
        )
        assert result["returncode"] == 0
        assert result["permission_decision"] == "allow"


class TestGitCommitRestriction:
    """Test git commit restriction to code-review agent."""

    def test_blocks_git_commit_for_developer(self):
        """Should block git commit for non-code-review agents."""
        result = run_validation(
            "Bash",
            {
                "command": "git commit -m 'test commit'",
                "subagent_type": "developer"
            }
        )
        assert result["returncode"] == 1
        assert result["permission_decision"] == "deny"
        assert "code-review" in result["reason"]

    def test_allows_git_commit_for_code_review(self):
        """Should allow git commit for code-review agent."""
        result = run_validation(
            "Bash",
            {
                "command": "git commit -m 'test commit'",
                "subagent_type": "code-review"
            }
        )
        assert result["returncode"] == 0
        assert result["permission_decision"] == "allow"

    def test_allows_git_commit_with_no_verify(self):
        """Should allow git commit with --no-verify flag."""
        result = run_validation(
            "Bash",
            {
                "command": "git commit --no-verify -m 'test'",
                "subagent_type": "developer"
            }
        )
        assert result["returncode"] == 0
        assert result["permission_decision"] == "allow"


class TestProtectedFileRestriction:
    """Test protected file modification restriction."""

    def test_blocks_claude_config_edit_for_developer(self):
        """Should block .claude config edits for non-trainer agents."""
        result = run_validation(
            "Edit",
            {
                "file_path": str(WORKING_DIR / ".claude/settings.json"),
                "old_string": "old",
                "new_string": "new",
                "subagent_type": "developer"
            }
        )
        assert result["returncode"] == 1
        assert result["permission_decision"] == "deny"
        assert "trainer" in result["reason"]

    def test_allows_claude_config_edit_for_trainer(self):
        """Should allow .claude config edits for trainer agent."""
        result = run_validation(
            "Edit",
            {
                "file_path": str(WORKING_DIR / ".claude/settings.json"),
                "old_string": "old",
                "new_string": "new",
                "subagent_type": "trainer"
            }
        )
        assert result["returncode"] == 0
        assert result["permission_decision"] == "allow"


if __name__ == "__main__":
    # Allow running with: python test_validate_tool_pytest.py
    pytest.main([__file__, "-v"])
