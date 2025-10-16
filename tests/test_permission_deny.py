#!/usr/bin/env python3
"""
Test that .claude/settings.json deny rules are enforced correctly.

This test verifies:
1. Deny rules block file operations as expected
2. Subagent frontmatter tools cannot override global deny rules
"""

import json
import subprocess
import tempfile
from pathlib import Path

import pytest

# Disable pytest timeout for these tests - they wait for subprocess completion
pytestmark = pytest.mark.timeout(0)


def test_permission_deny_exact_match(tmp_path):
    """Test that exact filename deny rules work."""
    # Create a test project directory
    test_dir = tmp_path / "test_project"
    test_dir.mkdir()

    # Create .claude/settings.json with deny rule
    claude_dir = test_dir / ".claude"
    claude_dir.mkdir()

    settings = {
        "permissions": {
            "deny": [
                "Write(./test-exact-match.txt)"
            ]
        }
    }

    (claude_dir / "settings.json").write_text(json.dumps(settings, indent=2))

    # Try to create the denied file using Claude Code CLI
    result = subprocess.run(
        [
            "claude",
            "-p", "please create a file called test-exact-match.txt with content 'testing'"
        ],
        cwd=test_dir,
        capture_output=True,
        text=True,
        timeout=30
    )

    # Check if file was created (should NOT be created if deny works)
    denied_file = test_dir / "test-exact-match.txt"

    # Assert that deny rule prevented creation
    assert not denied_file.exists(), (
        "Deny rule failed: file was created despite being in deny list. "
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_permission_deny_glob_pattern(tmp_path):
    """Test that glob pattern deny rules work."""
    test_dir = tmp_path / "test_project"
    test_dir.mkdir()

    claude_dir = test_dir / ".claude"
    claude_dir.mkdir()

    settings = {
        "permissions": {
            "deny": [
                "Write(./test-*.txt)"
            ]
        }
    }

    (claude_dir / "settings.json").write_text(json.dumps(settings, indent=2))

    # Try to create file matching glob pattern
    result = subprocess.run(
        [
            "claude",
            "-p", "please create a file called test-glob-pattern.txt with content 'testing'"
        ],
        cwd=test_dir,
        capture_output=True,
        text=True,
        timeout=30
    )

    denied_file = test_dir / "test-glob-pattern.txt"

    assert not denied_file.exists(), (
        "Glob pattern deny rule failed: file was created despite matching deny pattern. "
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_subagent_cannot_override_deny(tmp_path):
    """Test that subagent frontmatter tools cannot override global deny rules."""
    test_dir = tmp_path / "test_project"
    test_dir.mkdir()

    # Create .claude directory with settings and test agent
    claude_dir = test_dir / ".claude"
    claude_dir.mkdir()
    agents_dir = claude_dir / "agents"
    agents_dir.mkdir()

    # Create settings with deny rule
    settings = {
        "permissions": {
            "deny": [
                "Write(./test-denied.txt)"
            ]
        }
    }
    (claude_dir / "settings.json").write_text(json.dumps(settings, indent=2))

    # Create test agent with Write in tools
    agent_content = """---
name: test-writer-agent
tools: Write, Read
---

Test agent with Write tool in frontmatter.
"""
    (agents_dir / "test-writer-agent.md").write_text(agent_content)

    # Try to use subagent to write denied file
    result = subprocess.run(
        [
            "claude",
            "-p", "@agent-test-writer-agent please create a file called test-denied.txt with content 'testing'"
        ],
        cwd=test_dir,
        capture_output=True,
        text=True,
        timeout=30
    )

    denied_file = test_dir / "test-denied.txt"

    assert not denied_file.exists(), (
        "Subagent override vulnerability: subagent bypassed global deny rule. "
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_permission_deny_does_not_block_allowed_files(tmp_path):
    """Test that deny rules don't block files outside the pattern."""
    test_dir = tmp_path / "test_project"
    test_dir.mkdir()

    claude_dir = test_dir / ".claude"
    claude_dir.mkdir()

    settings = {
        "permissions": {
            "allow": [
                "Write"
            ],
            "deny": [
                "Write(./test-*.txt)"
            ]
        }
    }

    (claude_dir / "settings.json").write_text(json.dumps(settings, indent=2))

    # Try to create file NOT matching deny pattern
    result = subprocess.run(
        [
            "claude",
            "-p", "please create a file called allowed-file.txt with content 'testing'"
        ],
        cwd=test_dir,
        capture_output=True,
        text=True,
        timeout=30
    )

    allowed_file = test_dir / "allowed-file.txt"

    assert allowed_file.exists(), (
        "Deny rule too broad: blocked file that should be allowed. "
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert allowed_file.read_text() == "testing"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
