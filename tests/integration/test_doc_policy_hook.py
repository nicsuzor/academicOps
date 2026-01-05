"""Integration tests for PreToolUse hook documentation policy.

Tests verify that the PreToolUse hook correctly:
- Blocks *-GUIDE.md files
- Blocks .md files > 200 lines
- Allows normal .md files under the limit
"""

import json
import subprocess
from pathlib import Path

import pytest


def invoke_hook(tool_name: str, args: dict) -> dict:
    """Invoke PreToolUse hook script with JSON input.

    Per Claude Code docs:
    - Exit 0 = allow, JSON on stdout
    - Exit 2 = block, message on stderr

    Returns dict with:
    - "blocked": True if exit code 2
    - "message": stderr content if blocked
    - Other fields from stdout JSON if allowed
    """
    hook_script = Path(__file__).parent.parent.parent / "hooks" / "policy_enforcer.py"
    assert hook_script.exists(), f"Hook script not found: {hook_script}"

    hook_input = {
        "session_id": "test-session",
        "tool_name": tool_name,
        "tool_input": args,
    }

    result = subprocess.run(
        ["python3", str(hook_script)],
        input=json.dumps(hook_input),
        capture_output=True,
        text=True,
        check=False,
    )

    # Exit code 2 = blocked (per Claude Code hook docs)
    if result.returncode == 2:
        return {
            "blocked": True,
            "continue": False,
            "systemMessage": result.stderr.strip(),
        }

    # Exit code 0 = allowed
    assert (
        result.returncode == 0
    ), f"Unexpected exit code {result.returncode}: {result.stderr}"

    if result.stdout.strip():
        return json.loads(result.stdout)
    return {}


@pytest.mark.integration
def test_blocks_guide_md_files() -> None:
    """Test that hook blocks *-GUIDE.md files."""
    response = invoke_hook(
        tool_name="Write",
        args={
            "file_path": "/some/path/SETUP-GUIDE.md",
            "content": "# Setup Guide\n\nSome content.",
        },
    )

    assert response.get("continue") is False, "Hook should block GUIDE.md files"
    assert "BLOCKED" in response.get("systemMessage", "")
    assert "GUIDE" in response.get("systemMessage", "").upper()


@pytest.mark.integration
def test_blocks_md_over_200_lines() -> None:
    """Test that hook blocks .md files exceeding 200 lines."""
    long_content = "\n".join([f"Line {i}" for i in range(210)])

    response = invoke_hook(
        tool_name="Write",
        args={
            "file_path": "/some/path/document.md",
            "content": long_content,
        },
    )

    assert response.get("continue") is False, "Hook should block .md files > 200 lines"
    assert "BLOCKED" in response.get("systemMessage", "")
    assert (
        "200" in response.get("systemMessage", "")
        or "line" in response.get("systemMessage", "").lower()
    )


@pytest.mark.integration
def test_allows_md_under_200_lines() -> None:
    """Test that hook allows .md files under 200 lines."""
    short_content = "\n".join([f"Line {i}" for i in range(150)])

    response = invoke_hook(
        tool_name="Write",
        args={
            "file_path": "/some/path/document.md",
            "content": short_content,
        },
    )

    # Empty response or continue=True means allowed
    if response:
        assert (
            response.get("continue") is not False
        ), "Hook should allow .md files < 200 lines"


@pytest.mark.integration
def test_allows_non_md_files() -> None:
    """Test that hook allows non-.md files regardless of length."""
    long_content = "\n".join([f"Line {i}" for i in range(500)])

    response = invoke_hook(
        tool_name="Write",
        args={
            "file_path": "/some/path/script.py",
            "content": long_content,
        },
    )

    if response:
        assert response.get("continue") is not False, "Hook should allow non-.md files"


@pytest.mark.integration
def test_boundary_exactly_200_lines() -> None:
    """Test that hook allows exactly 200 lines (boundary case)."""
    content_200 = "\n".join([f"Line {i}" for i in range(200)])

    response = invoke_hook(
        tool_name="Write",
        args={
            "file_path": "/some/path/document.md",
            "content": content_200,
        },
    )

    if response:
        assert (
            response.get("continue") is not False
        ), "Hook should allow exactly 200 lines"


@pytest.mark.integration
def test_boundary_201_lines_blocked() -> None:
    """Test that hook blocks 201 lines (just over boundary)."""
    content_201 = "\n".join([f"Line {i}" for i in range(201)])

    response = invoke_hook(
        tool_name="Write",
        args={
            "file_path": "/some/path/document.md",
            "content": content_201,
        },
    )

    assert response.get("continue") is False, "Hook should block 201 lines"
