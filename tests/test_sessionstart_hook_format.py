"""Unit test for SessionStart hook JSON output format validation.

Ensures hooks always return correct Claude Code format with hookSpecificOutput wrapper.
This prevents regression to flat format: {"additionalContext": "..."}

The SessionStart hook (hooks/sessionstart_load_axioms.py) MUST output:
{
    "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": "..."
    }
}
"""

import json
import os
import subprocess
from pathlib import Path

# AOPS root for PYTHONPATH (hooks use `from hooks.x import` which requires this)
AOPS_ROOT = Path(__file__).parent.parent


def test_sessionstart_hook_outputs_correct_json_format() -> None:
    """Verify SessionStart hook uses correct JSON format with hookSpecificOutput.

    This test validates that:
    1. Hook script runs successfully (exit code 0)
    2. Hook outputs valid JSON
    3. Root level has 'hookSpecificOutput' key (required by Claude Code)
    4. hookSpecificOutput contains 'hookEventName' = "SessionStart"
    5. hookSpecificOutput contains non-empty 'additionalContext' string

    Raises:
        AssertionError: If format validation fails with clear diagnostic message
        subprocess.CalledProcessError: If hook script fails to run
        json.JSONDecodeError: If output is not valid JSON
    """
    # Path to hook script
    aops_root = Path(__file__).parent.parent
    hook_script = aops_root / "hooks" / "sessionstart_load_axioms.py"

    # Verify hook script exists
    assert hook_script.exists(), f"Hook script not found at {hook_script}"

    # Run hook script with empty stdin
    env = {**os.environ, "PYTHONPATH": str(AOPS_ROOT)}
    result = subprocess.run(
        ["python3", str(hook_script)],
        capture_output=True,
        text=True,
        timeout=10,
        input="{}",  # Provide empty JSON input
        env=env,
    )

    # Validate exit code
    assert (
        result.returncode == 0
    ), f"Hook script failed with exit code {result.returncode}\nstderr: {result.stderr}"

    # Parse JSON output
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise AssertionError(
            f"Hook output is not valid JSON. "
            f"Error: {e}\n"
            f"Output: {result.stdout}"
        ) from e

    # Validate hookSpecificOutput key exists at root level
    assert (
        "hookSpecificOutput" in output
    ), (
        f"Missing required 'hookSpecificOutput' key at root level. "
        f"Got keys: {list(output.keys())}. "
        f"This is a regression to flat format. "
        f"Claude Code requires wrapped format."
    )

    hook_output = output["hookSpecificOutput"]

    # Validate it's a dict
    assert isinstance(
        hook_output, dict
    ), f"hookSpecificOutput must be a dict, got {type(hook_output)}"

    # Validate hookEventName exists and equals "SessionStart"
    assert (
        "hookEventName" in hook_output
    ), f"Missing 'hookEventName' in hookSpecificOutput. Keys: {list(hook_output.keys())}"

    assert (
        hook_output["hookEventName"] == "SessionStart"
    ), (
        f"hookEventName must be 'SessionStart', "
        f"got '{hook_output['hookEventName']}'"
    )

    # Validate additionalContext exists and is non-empty string
    assert (
        "additionalContext" in hook_output
    ), f"Missing 'additionalContext' in hookSpecificOutput. Keys: {list(hook_output.keys())}"

    additional_context = hook_output["additionalContext"]
    assert isinstance(
        additional_context, str
    ), f"additionalContext must be string, got {type(additional_context)}"

    assert (
        len(additional_context) > 0
    ), "additionalContext must be non-empty string"

    # Validate additionalContext contains expected content markers
    assert "Framework Principles" in additional_context, (
        "additionalContext should contain Framework Principles section. "
        "This indicates AXIOMS.md was not loaded."
    )

    assert "User Context" in additional_context, (
        "additionalContext should contain User Context section. "
        "This indicates CORE.md was not loaded."
    )


if __name__ == "__main__":
    test_sessionstart_hook_outputs_correct_json_format()
    print("✓ SessionStart hook format validation passed")
