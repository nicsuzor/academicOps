"""Unit test for request_scribe hook (memory reminder injection).

Tests that the hook:
1. Injects reminder on Stop events
2. Injects reminder on PostToolUse with TodoWrite
3. Does NOT inject reminder on other PostToolUse events
4. Uses correct hookSpecificOutput format
5. Reads message from template file
"""

import json
import subprocess
from pathlib import Path


def run_hook(input_data: dict, expected_exit_code: int = 0) -> dict:
    """Run the request_scribe hook with given input."""
    aops_root = Path(__file__).parent.parent
    hook_script = aops_root / "hooks" / "request_scribe.py"

    assert hook_script.exists(), f"Hook script not found at {hook_script}"

    result = subprocess.run(
        ["python3", str(hook_script)],
        capture_output=True,
        text=True,
        timeout=10,
        input=json.dumps(input_data),
        env={"AOPS": str(aops_root)},
    )

    assert result.returncode == expected_exit_code, f"Hook exit code {result.returncode}, expected {expected_exit_code}: {result.stderr}"
    return json.loads(result.stdout)


def test_stop_event_injects_reminder() -> None:
    """Stop event should inject memory reminder via reason field."""
    output = run_hook({"hook_event_name": "Stop"}, expected_exit_code=1)

    # Stop hooks use reason/continue format, not hookSpecificOutput
    assert "reason" in output
    # Check for key phrase from the reminder (case-insensitive)
    assert "remember skill" in output["reason"].lower() or "remember" in output["reason"].lower()
    assert output.get("continue") is True


def test_todowrite_injects_reminder() -> None:
    """PostToolUse with TodoWrite should inject reminder."""
    output = run_hook({
        "hook_event_name": "PostToolUse",
        "tool_name": "TodoWrite"
    })

    assert "hookSpecificOutput" in output
    hook_output = output["hookSpecificOutput"]
    assert "additionalContext" in hook_output
    assert len(hook_output["additionalContext"]) > 0


def test_other_tool_no_reminder() -> None:
    """PostToolUse with non-TodoWrite tool should NOT inject reminder."""
    output = run_hook({
        "hook_event_name": "PostToolUse",
        "tool_name": "Read"
    })

    # Should return empty dict (no reminder)
    assert output == {} or "additionalContext" not in output.get("hookSpecificOutput", {})


def test_template_file_exists() -> None:
    """Template file should exist at expected location."""
    aops_root = Path(__file__).parent.parent
    template = aops_root / "hooks" / "prompts" / "memory-reminder.md"
    assert template.exists(), f"Template not found at {template}"
    content = template.read_text()
    assert len(content) > 0, "Template is empty"


if __name__ == "__main__":
    test_stop_event_injects_reminder()
    print("✓ Stop event test passed")
    test_todowrite_injects_reminder()
    print("✓ TodoWrite test passed")
    test_other_tool_no_reminder()
    print("✓ Other tool test passed")
    test_template_file_exists()
    print("✓ Template file test passed")
