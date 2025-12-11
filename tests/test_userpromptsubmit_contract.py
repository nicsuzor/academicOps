"""Contract test for UserPromptSubmit hook input schema compliance.

Verifies that the hook correctly reads from Claude Code's REAL input schema.
Claude Code sends: {"session_id": "...", "prompt": "user message", "cwd": "..."}

This test MUST fail if someone changes the field name from 'prompt' to anything else
(like 'userMessage' or 'message'), which would break integration with Claude Code.
"""

import json
import subprocess
from pathlib import Path


def test_userpromptsubmit_reads_prompt_field_from_claude_code_schema(
    tmp_path: Path,
) -> None:
    """Verify hook reads 'prompt' field from Claude Code's actual input schema.

    This test validates that:
    1. Hook accepts Claude Code's REAL input format with 'prompt' field
    2. Hook extracts user message from 'prompt' field (NOT 'userMessage')
    3. Hook writes activity log entry to correct location
    4. Activity log contains the user's message from 'prompt' field

    The test uses subprocess to run the hook with realistic input and verifies
    the activity log output. This ensures the hook contract matches Claude Code's
    actual behavior.

    If this test fails, someone likely changed 'prompt' to a wrong field name,
    breaking integration with Claude Code.

    Args:
        tmp_path: pytest fixture providing temporary directory

    Raises:
        AssertionError: If hook uses wrong field name or fails to log activity
        subprocess.CalledProcessError: If hook script fails to run
        json.JSONDecodeError: If hook output is not valid JSON
    """
    # Setup temporary ACA_DATA directory for activity log
    temp_data_dir = tmp_path / "aca_data"
    activity_log_path = temp_data_dir / "logs" / "activity.jsonl"
    temp_data_dir.mkdir(parents=True)

    # Path to hook script
    aops_root = Path(__file__).parent.parent
    hook_script = aops_root / "hooks" / "log_userpromptsubmit.py"

    # Verify hook script exists
    assert hook_script.exists(), f"Hook script not found at {hook_script}"

    # Create Claude Code's REAL input schema
    # This is what Claude Code actually sends to the hook
    test_message = "Test user prompt for contract validation"
    claude_code_input = {
        "session_id": "test-session-123",
        "prompt": test_message,  # This is the REAL field name from Claude Code
        "cwd": str(aops_root),
    }

    # Run hook script with Claude Code's real input format
    result = subprocess.run(
        ["python3", str(hook_script)],
        capture_output=True,
        text=True,
        timeout=10,
        input=json.dumps(claude_code_input),
        env={
            "AOPS": str(aops_root),
            "ACA_DATA": str(temp_data_dir),
            "PATH": subprocess.os.environ.get("PATH", ""),
            "PYTHONPATH": str(aops_root),
        },
    )

    # Validate hook ran successfully
    assert result.returncode == 0, (
        f"Hook script failed with exit code {result.returncode}\n"
        f"stderr: {result.stderr}\n"
        f"stdout: {result.stdout}"
    )

    # Parse hook output
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise AssertionError(
            f"Hook output is not valid JSON. "
            f"Error: {e}\n"
            f"Output: {result.stdout}"
        ) from e

    # Validate hookSpecificOutput structure
    assert "hookSpecificOutput" in output, (
        f"Missing required 'hookSpecificOutput' key. "
        f"Got keys: {list(output.keys())}"
    )

    hook_output = output["hookSpecificOutput"]
    assert hook_output["hookEventName"] == "UserPromptSubmit"

    # Verify activity log was created and contains the message
    assert activity_log_path.exists(), (
        f"Activity log not created at {activity_log_path}. "
        f"Hook may have failed to write log or used wrong ACA_DATA path."
    )

    # Read activity log and verify it contains the user's message
    activity_entries = []
    with activity_log_path.open("r") as f:
        for line in f:
            if line.strip():
                activity_entries.append(json.loads(line))

    assert len(activity_entries) > 0, (
        f"Activity log is empty. Hook failed to log user prompt. "
        f"This likely means hook is reading wrong field name."
    )

    # Find the log entry for our test message
    # Hook logs to 'action' field via log_activity()
    found_message = False
    for entry in activity_entries:
        if "action" in entry and test_message in entry["action"]:
            found_message = True
            break

    assert found_message, (
        f"Activity log does not contain the user's message from 'prompt' field.\n"
        f"Expected message to appear in 'action': '{test_message}'\n"
        f"Activity log entries: {activity_entries}\n"
        f"\n"
        f"FAILURE: Hook is reading from wrong field name!\n"
        f"Claude Code sends 'prompt' field, but hook is not using it.\n"
        f"Check that hook reads: input_data.get('prompt', ...) (NOT 'userMessage')"
    )


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-xvs"])
