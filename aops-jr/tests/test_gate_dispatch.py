"""Tests for gate dispatcher (aops-jr plugin)."""

import io
import json
import os
import subprocess
import sys
from pathlib import Path

_JR_HOOKS = str(Path(__file__).resolve().parent.parent / "hooks")
if _JR_HOOKS not in sys.path:
    sys.path.insert(0, _JR_HOOKS)

import gate_dispatch
from gates.verdict import deny

from tests.paths import get_hook_script


def _run(raw: dict, client: str = "claude", env: dict | None = None) -> subprocess.CompletedProcess:
    repo_root = Path(__file__).resolve().parent.parent.parent
    dispatch_path = repo_root / "aops-jr" / "hooks" / "gate_dispatch.py"
    if not dispatch_path.exists():
        dispatch_path = repo_root / "aops" / "hooks" / "gate_dispatch.py"
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
    assert result.stdout != ""
    output = json.loads(result.stdout)
    assert "additionalContext" in output["hookSpecificOutput"]


def test_pretooluse_agent_with_model_produces_no_output():
    raw = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Agent",
        "tool_input": {"subagent_type": "james", "model": "haiku"},
        "session_id": "dispatch-test-agent-with-model",
    }
    result = _run(raw)
    assert result.stdout == ""


def test_pretooluse_other_tool_produces_no_output():
    raw = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "ls -la"},
        "session_id": "dispatch-test-safe",
    }
    result = _run(raw)
    assert result.stdout == ""


def test_stop_warns_once_per_session_via_isolated_state_dir(tmp_path):
    env = {**os.environ, "AOPS_GATE_STATE_DIR": str(tmp_path)}
    raw = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Agent",
        "tool_input": {"subagent_type": "james"},
        "session_id": "dispatch-test-agent-warn",
    }

    first = _run(raw, env=env)
    assert first.stdout != ""


def test_stop_hook_active_is_a_no_op(tmp_path):
    env = {**os.environ, "AOPS_GATE_STATE_DIR": str(tmp_path)}
    raw = {
        "hook_event_name": "Stop",
        "session_id": "dispatch-test-stop-loop",
        "stop_hook_active": True,
    }
    result = _run(raw, env=env)
    assert result.stdout == ""


def test_subagentstop_hook_active_is_a_no_op(tmp_path):
    env = {**os.environ, "AOPS_GATE_STATE_DIR": str(tmp_path)}
    raw = {
        "hook_event_name": "SubagentStop",
        "session_id": "dispatch-test-subagent-stop-loop",
        "stop_hook_active": True,
    }
    result = _run(raw, env=env)
    assert result.stdout == ""


def test_a_raising_gate_cannot_suppress_another_gates_deny(monkeypatch, capsys):
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

    rc = gate_dispatch.main()
    assert rc == 0

    captured = capsys.readouterr()
    assert "legitimate deny that must still emit" in captured.out
    assert "raising_gate" in captured.err
