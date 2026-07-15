"""End-to-end: stdin JSON -> gate_dispatch.py -> stdout wire JSON."""

import json
import os
import subprocess
import sys

from tests.paths import get_hook_script


def _run(raw: dict, client: str = "claude", env: dict | None = None):
    dispatch_path = get_hook_script("gate_dispatch.py")
    result = subprocess.run(
        [sys.executable, str(dispatch_path), client],
        input=json.dumps(raw),
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    return result


def test_pretooluse_rm_rf_is_denied():
    raw = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "rm -rf /tmp/whatever"},
        "session_id": "dispatch-test-rm-rf",
    }
    result = _run(raw)
    output = json.loads(result.stdout)
    assert output["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_pretooluse_safe_command_produces_no_output():
    raw = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "ls -la"},
        "session_id": "dispatch-test-safe",
    }
    result = _run(raw)
    assert result.stdout.strip() == ""


def test_stop_warns_once_per_session_via_isolated_state_dir(tmp_path):
    env = {**os.environ, "AOPS_GATE_STATE_DIR": str(tmp_path)}
    raw = {"hook_event_name": "Stop", "session_id": "dispatch-test-stop"}

    first = _run(raw, env=env)
    first_output = json.loads(first.stdout)
    assert first_output["hookSpecificOutput"]["additionalContext"]

    second = _run(raw, env=env)
    assert second.stdout.strip() == ""
