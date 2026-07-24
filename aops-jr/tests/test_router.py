"""Tests for aops-jr's face-discipline hook router (aops-jr/hooks/router.py).

Per specs/packaging/v0.5-modular-topology.md's disposition table, the
SubagentStop / UserPromptSubmit / PostToolUse injection branches are jr/ida's
exclusive concern (core's router.py carries only SessionStart credential
isolation + PreToolUse headless fail-fast). These PostToolUse cases were
moved here from tests/test_router.py, which previously duplicated coverage
of a byte-identical branch that had been copied (not moved) into core's
router.py by commit ab9d9e4da — see epic_21042b5f.
"""

import json
import subprocess
import sys
from pathlib import Path

_ROUTER_PATH = Path(__file__).resolve().parent.parent / "hooks" / "router.py"


def _run_router(input_data: dict, client: str = "claude", event: str | None = None) -> subprocess.CompletedProcess:
    assert _ROUTER_PATH.exists(), f"router.py not found at {_ROUTER_PATH}"
    args = [sys.executable, str(_ROUTER_PATH), client]
    if event:
        args.append(event)
    return subprocess.run(
        args,
        input=json.dumps(input_data),
        capture_output=True,
        text=True,
        check=True,
    )


def test_posttooluse_agent_synchronous_emits_reminder():
    """Synchronous Agent tool calls (run_in_background not set or False) emit the verify reminder."""
    input_data = {
        "hook_event_name": "PostToolUse",
        "tool_name": "Agent",
        "tool_input": {"prompt": "do research"},
    }
    result = _run_router(input_data, client="claude", event="PostToolUse")
    assert result.returncode == 0
    parsed = json.loads(result.stdout)
    assert "≡ Always check subagent outputs" in parsed.get("systemMessage", "")
    assert "additionalContext" in parsed.get("hookSpecificOutput", {})


def test_posttooluse_agent_background_suppressed():
    """Background Agent tool calls (run_in_background=True) suppress the verify reminder."""
    input_data = {
        "hook_event_name": "PostToolUse",
        "tool_name": "Agent",
        "tool_input": {"prompt": "do research", "run_in_background": True},
    }
    result = _run_router(input_data, client="claude", event="PostToolUse")
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_subagentstop_emits_honesty_reminder():
    """SubagentStop emits the honesty/output-format reminder unless stop_hook_active is set."""
    input_data = {
        "hook_event_name": "SubagentStop",
        "stop_hook_active": False,
        "agent_id": "test-agent",
        "agent_type": "general-purpose",
    }
    result = _run_router(input_data, client="claude", event="SubagentStop")
    assert result.returncode == 0
    parsed = json.loads(result.stdout)
    assert "additionalContext" in parsed.get("hookSpecificOutput", {})


def test_subagentstop_suppressed_when_stop_hook_active():
    """SubagentStop suppresses the reminder when stop_hook_active is already set (no re-loop)."""
    input_data = {
        "hook_event_name": "SubagentStop",
        "stop_hook_active": True,
    }
    result = _run_router(input_data, client="claude", event="SubagentStop")
    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_userpromptsubmit_emits_hydrate_reminder():
    """UserPromptSubmit always emits the hydrate reminder."""
    input_data = {"hook_event_name": "UserPromptSubmit"}
    result = _run_router(input_data, client="claude", event="UserPromptSubmit")
    assert result.returncode == 0
    parsed = json.loads(result.stdout)
    assert "additionalContext" in parsed.get("hookSpecificOutput", {})
