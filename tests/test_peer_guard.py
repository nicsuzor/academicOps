"""Unit tests for the main Ida peer guard hook.

Validates that the conversational main Ida context is structurally blocked
from directly spawning or messaging Pauli or Sara, while allowing subagents
to delegate without restriction. Asserts against configuration loaded from
tests/policy.toml (Policy as Code).
"""

from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
IDA_HOOKS = REPO_ROOT / "plugins" / "ida" / "hooks"

if str(IDA_HOOKS) not in sys.path:
    sys.path.insert(0, str(IDA_HOOKS))

from dispatch import HookContext, Kind, render  # type: ignore[import-not-found]
from peer_guard import peer_guard  # type: ignore[import-not-found]

POLICY_FILE = REPO_ROOT / "tests" / "policy.toml"
_POLICY = tomllib.loads(POLICY_FILE.read_text(encoding="utf-8"))
PEER_GUARD_POLICY = _POLICY["ida"]["peer_guard"]
BLOCKED_PEERS: list[str] = PEER_GUARD_POLICY["blocked_peers"]
DELEGATION_TARGET: str = PEER_GUARD_POLICY["delegation_target"]
REFUSAL_INDICATOR: str = PEER_GUARD_POLICY["refusal_indicator"]


# ---------------------------------------------------------------------------
# Unit tests: direct handler evaluation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("peer", BLOCKED_PEERS)
@pytest.mark.parametrize("tool", ["Agent", "invoke_subagent", "task"])
@pytest.mark.parametrize("prefix", ["", "ida:"])
def test_main_thread_subagent_spawn_blocked(peer: str, tool: str, prefix: str):
    """Main thread spawning a blocked peer returns Kind.REFUSE."""
    subagent_type = f"{prefix}{peer}"
    ctx = HookContext(
        client="claude",
        event="PreToolUse",
        tool=tool,
        agent_id="",  # Main thread
        tool_input={"subagent_type": subagent_type, "TypeName": subagent_type},
    )
    result = peer_guard(ctx)
    assert result is not None
    assert result.kind is Kind.REFUSE
    assert REFUSAL_INDICATOR in result.inject_text


@pytest.mark.parametrize("peer", BLOCKED_PEERS)
@pytest.mark.parametrize("tool", ["SendMessage", "send_message"])
@pytest.mark.parametrize("prefix", ["", "ida:"])
def test_main_thread_send_message_blocked(peer: str, tool: str, prefix: str):
    """Main thread messaging a blocked peer returns Kind.REFUSE."""
    target = f"{prefix}{peer}"
    ctx = HookContext(
        client="claude",
        event="PreToolUse",
        tool=tool,
        agent_id="",  # Main thread
        tool_input={"to": target, "recipient": target},
    )
    result = peer_guard(ctx)
    assert result is not None
    assert result.kind is Kind.REFUSE
    assert REFUSAL_INDICATOR in result.inject_text


@pytest.mark.parametrize("peer", BLOCKED_PEERS)
def test_subagent_spawn_allowed(peer: str):
    """When ctx.agent_id is present (subagent), calls pass through (AC-HOOK-2)."""
    ctx = HookContext(
        client="claude",
        event="PreToolUse",
        tool="Agent",
        agent_id="subagent-42",  # Running inside a subagent
        tool_input={"subagent_type": peer},
    )
    result = peer_guard(ctx)
    assert result is None


@pytest.mark.parametrize("peer", BLOCKED_PEERS)
def test_subagent_send_message_allowed(peer: str):
    """When ctx.agent_id is present (subagent), messaging passes through."""
    ctx = HookContext(
        client="claude",
        event="PreToolUse",
        tool="SendMessage",
        agent_id="subagent-42",  # Running inside a subagent
        tool_input={"to": peer},
    )
    result = peer_guard(ctx)
    assert result is None


def test_main_thread_allowed_tool_calls():
    """Tool calls to other agents or normal tools are permitted."""
    allowed_calls = [
        HookContext(
            client="claude",
            event="PreToolUse",
            tool="Agent",
            agent_id="",
            tool_input={"subagent_type": DELEGATION_TARGET},
        ),
        HookContext(
            client="claude",
            event="PreToolUse",
            tool="Agent",
            agent_id="",
            tool_input={"subagent_type": "marsha"},
        ),
        HookContext(
            client="claude",
            event="PreToolUse",
            tool="SendMessage",
            agent_id="",
            tool_input={"to": "user"},
        ),
        HookContext(
            client="claude",
            event="PreToolUse",
            tool="read_file",
            agent_id="",
            tool_input={"Path": "/workspace/README.md"},
        ),
    ]
    for ctx in allowed_calls:
        assert peer_guard(ctx) is None


# ---------------------------------------------------------------------------
# Wire format rendering across clients (AC-HOOK-4)
# ---------------------------------------------------------------------------


def test_wire_render_claude_refusal():
    """Claude Code wire format renders permissionDecision: 'deny'."""
    ctx = HookContext(
        client="claude",
        event="PreToolUse",
        tool="Agent",
        agent_id="",
        tool_input={"subagent_type": BLOCKED_PEERS[0]},
    )
    result = peer_guard(ctx)
    assert result is not None
    output = render("claude", "PreToolUse", result)
    specific = output.get("hookSpecificOutput", {})
    assert specific.get("permissionDecision") == "deny"
    assert REFUSAL_INDICATOR in specific.get("permissionDecisionReason", "")


def test_wire_render_agy_refusal():
    """Antigravity (agy) wire format renders decision: 'deny'."""
    ctx = HookContext(
        client="agy",
        event="PreToolUse",
        tool="invoke_subagent",
        agent_id="",
        tool_input={"TypeName": BLOCKED_PEERS[0]},
    )
    result = peer_guard(ctx)
    assert result is not None
    output = render("agy", "PreToolUse", result)
    assert output.get("decision") == "deny"
    assert REFUSAL_INDICATOR in output.get("reason", "")


# ---------------------------------------------------------------------------
# End-to-end integration via dispatch.py subprocess
# ---------------------------------------------------------------------------


def test_dispatch_e2e_blocks_main_thread(tmp_path: Path):
    """Running dispatch.py end-to-end on Claude Code denies blocked peer spawn."""
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Agent",
        "tool_input": {"subagent_type": BLOCKED_PEERS[0]},
        "session_id": "test-sess",
    }
    proc = subprocess.run(
        [sys.executable, str(IDA_HOOKS / "dispatch.py"), "claude", "PreToolUse"],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=tmp_path,
        timeout=10,
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert REFUSAL_INDICATOR in data["hookSpecificOutput"]["permissionDecisionReason"]


def test_dispatch_e2e_allows_subagent(tmp_path: Path):
    """Running dispatch.py end-to-end allows call when agent_id is present."""
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Agent",
        "tool_input": {"subagent_type": BLOCKED_PEERS[0]},
        "agent_id": "subagent-123",
        "session_id": "test-sess",
    }
    proc = subprocess.run(
        [sys.executable, str(IDA_HOOKS / "dispatch.py"), "claude", "PreToolUse"],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        cwd=tmp_path,
        timeout=10,
    )
    assert proc.returncode == 0, proc.stderr
    # No denial output
    if proc.stdout.strip():
        data = json.loads(proc.stdout)
        specific = data.get("hookSpecificOutput", {})
        assert specific.get("permissionDecision") != "deny"


# ---------------------------------------------------------------------------
# Fail-closed robustness (AC-HOOK-3)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("invalid_input", ["not valid json", "{broken:", ""])
def test_dispatch_fail_closed_on_invalid_json(tmp_path: Path, invalid_input: str):
    """dispatch.py fails closed with exit code 2 on invalid JSON input."""
    if not invalid_input:
        pytest.skip("empty stdin on non-tty is handled gracefully")
    proc = subprocess.run(
        [sys.executable, str(IDA_HOOKS / "dispatch.py"), "claude", "PreToolUse"],
        input=invalid_input,
        text=True,
        capture_output=True,
        cwd=tmp_path,
        timeout=10,
    )
    assert proc.returncode == 2
    assert "not valid JSON" in proc.stderr


@pytest.mark.parametrize("non_dict_json", ["[1, 2, 3]", '"string"', "123", "true"])
def test_dispatch_fail_closed_on_non_object_json(tmp_path: Path, non_dict_json: str):
    """dispatch.py fails closed with exit code 2 on non-object JSON input."""
    proc = subprocess.run(
        [sys.executable, str(IDA_HOOKS / "dispatch.py"), "claude", "PreToolUse"],
        input=non_dict_json,
        text=True,
        capture_output=True,
        cwd=tmp_path,
        timeout=10,
    )
    assert proc.returncode == 2
    assert "JSON object" in proc.stderr


def test_peer_guard_standalone_cli(tmp_path: Path):
    """peer_guard.py run standalone blocks with exit code 2 and passes with exit code 0."""
    script = IDA_HOOKS / "peer_guard.py"

    # Blocked call -> exit code 2
    blocked_payload = {
        "tool_name": "Agent",
        "tool_input": {"subagent_type": BLOCKED_PEERS[0]},
    }
    proc_blocked = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(blocked_payload),
        text=True,
        capture_output=True,
        cwd=tmp_path,
        timeout=10,
    )
    assert proc_blocked.returncode == 2
    assert REFUSAL_INDICATOR in proc_blocked.stderr

    # Allowed call -> exit code 0
    allowed_payload = {
        "tool_name": "Agent",
        "tool_input": {"subagent_type": DELEGATION_TARGET},
    }
    proc_allowed = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(allowed_payload),
        text=True,
        capture_output=True,
        cwd=tmp_path,
        timeout=10,
    )
    assert proc_allowed.returncode == 0

    # Invalid JSON -> exit code 2
    proc_invalid = subprocess.run(
        [sys.executable, str(script)],
        input="invalid json",
        text=True,
        capture_output=True,
        cwd=tmp_path,
        timeout=10,
    )
    assert proc_invalid.returncode == 2
