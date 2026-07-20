"""End-to-end: stdin JSON -> gate_dispatch.py -> stdout wire JSON."""

import io
import json
import os
import subprocess
import sys

import gate_dispatch
from gates.verdict import deny

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


def test_pretooluse_agent_without_model_warns():
    raw = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Agent",
        "tool_input": {"subagent_type": "james"},
        "session_id": "dispatch-test-agent-no-model",
    }
    result = _run(raw)
    output = json.loads(result.stdout)
    assert output["hookSpecificOutput"]["additionalContext"]


def test_pretooluse_agent_with_model_produces_no_output():
    raw = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Agent",
        "tool_input": {"subagent_type": "james", "model": "haiku"},
        "session_id": "dispatch-test-agent-with-model",
    }
    result = _run(raw)
    assert result.stdout.strip() == ""


def test_pretooluse_other_tool_produces_no_output():
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


def test_stop_hook_active_is_a_no_op(tmp_path):
    """Self-loop guard: a re-fired Stop with stop_hook_active=True must not
    run any gate, touch state, or print anything — even on a session that
    has never been seen before (state can't be relied on to short-circuit
    it; the guard has to be structural, ahead of any gate)."""
    env = {**os.environ, "AOPS_GATE_STATE_DIR": str(tmp_path)}
    raw = {
        "hook_event_name": "Stop",
        "session_id": "dispatch-test-stop-loop",
        "stop_hook_active": True,
    }
    result = _run(raw, env=env)
    assert result.stdout.strip() == ""
    assert not list(tmp_path.glob("*.json"))


def test_subagentstop_hook_active_is_a_no_op(tmp_path):
    env = {**os.environ, "AOPS_GATE_STATE_DIR": str(tmp_path)}
    raw = {
        "hook_event_name": "SubagentStop",
        "session_id": "dispatch-test-subagent-stop-loop",
        "stop_hook_active": True,
    }
    result = _run(raw, env=env)
    assert result.stdout.strip() == ""


def test_a_raising_gate_cannot_suppress_another_gates_deny(monkeypatch, capsys):
    """Exception isolation: one gate raising must never crash the process
    or discard another gate's (especially a denying) verdict.

    In-process regression for the bug Marsha reproduced: a raising gate
    used to blow up the bare list comprehension in main(), so the whole
    process exited non-zero with empty stdout and a real deny from another
    gate was silently lost.
    """

    def raising_gate(event, state):
        raise RuntimeError("simulated gate failure")

    def denying_gate(event, state):
        return deny("legitimate deny that must still emit")

    monkeypatch.setattr(gate_dispatch, "GATES", [raising_gate, denying_gate])
    raw = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "ls"},
        "session_id": "dispatch-test-isolation",
    }
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(raw)))
    monkeypatch.setattr(sys, "argv", ["gate_dispatch.py", "claude"])

    rc = gate_dispatch.main()

    assert rc == 0
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert output["hookSpecificOutput"]["permissionDecisionReason"] == (
        "legitimate deny that must still emit"
    )
    assert "simulated gate failure" in captured.err
