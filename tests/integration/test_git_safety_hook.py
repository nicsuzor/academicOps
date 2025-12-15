"""Integration tests for PreToolUse hook git safety validation.

Tests verify that the PreToolUse hook correctly:
- Blocks destructive git commands (git reset --hard, git push --force)
- Allows safe git commands
- Returns proper error messages when blocking commands
"""

import json
import subprocess
from pathlib import Path

import pytest


def invoke_hook(tool_name: str, args: dict) -> dict:
    """Invoke PreToolUse hook script with JSON input.

    Args:
        tool_name: Name of the tool being invoked
        args: Tool arguments dictionary

    Returns:
        Hook response as dictionary
    """
    # Locate hook script
    hook_script = Path(__file__).parent.parent.parent / "hooks" / "policy_enforcer.py"
    assert hook_script.exists(), f"Hook script not found: {hook_script}"

    # Build hook input - matches Claude Code PreToolUse event format
    hook_input = {
        "session_id": "test-session",
        "tool_name": tool_name,
        "tool_input": args,
    }

    # Invoke hook with JSON input via stdin
    result = subprocess.run(
        ["python3", str(hook_script)],
        input=json.dumps(hook_input),
        capture_output=True,
        text=True,
        check=False,
    )

    # Per Claude Code docs:
    # - Exit 0: Allow, JSON in stdout is processed
    # - Exit 2: Block, only stderr is read (message to Claude)
    if result.returncode == 2:
        # Blocking response - return synthetic response with stderr message
        return {
            "continue": False,
            "systemMessage": result.stderr.strip(),
            "_exit_code": 2,
        }
    elif result.returncode != 0:
        raise AssertionError(f"Unexpected exit code {result.returncode}: {result.stderr}")

    # Parse hook response (exit 0)
    if result.stdout.strip():
        return json.loads(result.stdout)
    return {}


@pytest.mark.integration
def test_hook_blocks_git_reset_hard() -> None:
    """Test that hook blocks 'git reset --hard' command.

    Verifies:
    - Hook detects destructive git reset command
    - Hook returns continue=False
    - Hook provides clear error message explaining why command is blocked
    """
    response = invoke_hook(
        tool_name="Bash",
        args={
            "command": "git reset --hard",
            "description": "Reset repository to last commit",
        },
    )

    # Hook should block the command
    assert "continue" in response, "Hook response should include 'continue' key"
    assert response["continue"] is False, "Hook should block destructive git command"

    # Hook should provide explanation
    assert "systemMessage" in response, "Hook should provide system message"
    assert "git reset --hard" in response["systemMessage"].lower() or "destructive" in response["systemMessage"].lower(), \
        "Error message should mention the destructive command"


@pytest.mark.integration
def test_hook_blocks_git_push_force() -> None:
    """Test that hook blocks 'git push --force' command.

    Verifies:
    - Hook detects force push command
    - Hook returns continue=False
    - Hook provides clear error message
    """
    response = invoke_hook(
        tool_name="Bash",
        args={
            "command": "git push --force",
            "description": "Force push to remote",
        },
    )

    # Hook should block the command
    assert "continue" in response, "Hook response should include 'continue' key"
    assert response["continue"] is False, "Hook should block force push command"

    # Hook should provide explanation
    assert "systemMessage" in response, "Hook should provide system message"
    assert "force" in response["systemMessage"].lower() or "destructive" in response["systemMessage"].lower(), \
        "Error message should mention force push"


@pytest.mark.integration
def test_hook_allows_safe_git_commands() -> None:
    """Test that hook allows safe git commands.

    Verifies:
    - Hook allows safe git operations (status, log, diff)
    - Hook returns empty response (allows command to proceed)
    """
    safe_commands = [
        "git status",
        "git log --oneline",
        "git diff",
        "git add .",
        "git commit -m 'message'",
    ]

    for command in safe_commands:
        response = invoke_hook(
            tool_name="Bash",
            args={
                "command": command,
                "description": f"Run {command}",
            },
        )

        # Hook should allow command (empty response or continue=True)
        if "continue" in response:
            assert response["continue"] is True, f"Hook should allow safe command: {command}"
        # Empty response means continue
        assert "systemMessage" not in response or "BLOCKED" not in response.get("systemMessage", ""), \
            f"Hook should not block safe command: {command}"


@pytest.mark.integration
def test_hook_blocks_git_reset_hard_mixed_case() -> None:
    """Test that hook detects destructive commands regardless of flag order.

    Verifies:
    - Hook detects 'git reset --hard HEAD~1' (with additional arguments)
    - Detection is robust to variations in command syntax
    """
    response = invoke_hook(
        tool_name="Bash",
        args={
            "command": "git reset --hard HEAD~1",
            "description": "Reset to previous commit",
        },
    )

    # Hook should block the command
    assert "continue" in response, "Hook response should include 'continue' key"
    assert response["continue"] is False, "Hook should block git reset --hard with arguments"


@pytest.mark.integration
def test_hook_allows_non_bash_tools() -> None:
    """Test that hook only validates Bash tool commands.

    Verifies:
    - Hook ignores non-Bash tools (Read, Write, Edit)
    - Hook returns empty response for non-Bash tools
    """
    response = invoke_hook(
        tool_name="Read",
        args={
            "file_path": "/some/file.txt",
        },
    )

    # Hook should not interfere with non-Bash tools
    if "continue" in response:
        assert response["continue"] is not False, "Hook should not block non-Bash tools"
