"""Tests for the Claude Code PreToolUse hook injecting caller session into MCP calls."""

from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
IDA_HOOKS = REPO_ROOT / "plugins" / "ida" / "hooks"
HOOK_SCRIPT = IDA_HOOKS / "mcp_caller_session.py"
if str(IDA_HOOKS) not in sys.path:
    sys.path.insert(0, str(IDA_HOOKS))

_POLICY = tomllib.loads((REPO_ROOT / "tests" / "policy.toml").read_text(encoding="utf-8"))
SESSION_SERVERS = frozenset(
    _POLICY.get("hooks", {})
    .get("mcp_caller_session", {})
    .get("session_servers", ["pkb", "services"])
)


def test_hook_carries_session_ids_and_keeps_original_arguments():
    """Main thread call: hook output carries _session with stdin's ids, omits agent_id, keeps original arguments."""
    from mcp_caller_session import inject_caller_session

    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "mcp__pkb__get_task",
        "session_id": "sess-uuid-main",
        "prompt_id": "prompt-uuid-main",
        "tool_use_id": "toolu-01",
        "tool_input": {
            "id": "task_0c62b710",
        },
    }

    result = inject_caller_session(payload, session_servers=SESSION_SERVERS)
    assert "hookSpecificOutput" in result
    specific = result["hookSpecificOutput"]
    assert specific.get("hookEventName") == "PreToolUse"
    assert "permissionDecision" not in specific

    updated = specific.get("updatedInput")
    assert isinstance(updated, dict)
    # Original arguments kept
    assert updated.get("id") == "task_0c62b710"

    # _session injected
    assert "_session" in updated
    session = updated["_session"]
    assert session.get("session_id") == "sess-uuid-main"
    assert session.get("prompt_id") == "prompt-uuid-main"
    assert "agent_id" not in session


def test_hook_includes_agent_id_in_subagent():
    """Subagent call: hook output carries _session including agent_id from stdin."""
    from mcp_caller_session import inject_caller_session

    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "mcp__services__portal_codemode_execute",
        "session_id": "sess-uuid-parent",
        "agent_id": "subagent-uuid-child",
        "prompt_id": "prompt-uuid-turn",
        "tool_use_id": "toolu-02",
        "tool_input": {
            "code": "return await codemode.pkb_get_task({ id: 'task_0c62b710' });",
        },
    }

    result = inject_caller_session(payload, session_servers=SESSION_SERVERS)
    specific = result["hookSpecificOutput"]
    updated = specific["updatedInput"]

    # Original arguments kept
    assert updated["code"] == "return await codemode.pkb_get_task({ id: 'task_0c62b710' });"

    # _session includes agent_id
    session = updated["_session"]
    assert session["session_id"] == "sess-uuid-parent"
    assert session["agent_id"] == "subagent-uuid-child"
    assert session["prompt_id"] == "prompt-uuid-turn"


def test_hook_subprocess_execution():
    """End-to-end execution of the script as a subprocess reading stdin and emitting JSON stdout."""
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "mcp__pkb__search",
        "session_id": "sess-e2e",
        "agent_id": "agent-sub",
        "prompt_id": "prompt-e2e",
        "tool_use_id": "toolu-03",
        "tool_input": {"query": "observability"},
    }

    proc = subprocess.run(
        [sys.executable, str(HOOK_SCRIPT)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0, f"Hook failed with stderr: {proc.stderr}"
    data = json.loads(proc.stdout)
    updated = data["hookSpecificOutput"]["updatedInput"]
    assert updated["query"] == "observability"
    assert updated["_session"] == {
        "session_id": "sess-e2e",
        "agent_id": "agent-sub",
        "prompt_id": "prompt-e2e",
    }


def test_hook_subprocess_fails_on_malformed_stdin():
    """Verify that malformed JSON on stdin fails fast with a non-zero exit code."""
    proc = subprocess.run(
        [sys.executable, str(HOOK_SCRIPT)],
        input="invalid json {",
        text=True,
        capture_output=True,
    )
    assert proc.returncode != 0


def test_hook_carries_conversation_id_from_agy():
    """agy call: payload provides conversationId, hook injects session_id = conversationId."""
    from mcp_caller_session import inject_caller_session

    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "mcp__pkb__get_task",
        "conversationId": "conv-uuid-agy",
        "prompt_id": "prompt-uuid-agy",
        "tool_use_id": "toolu-04",
        "tool_input": {"id": "task-fixture-01"},
    }

    result = inject_caller_session(payload, session_servers=SESSION_SERVERS)
    session = result["hookSpecificOutput"]["updatedInput"]["_session"]
    assert session.get("session_id") == "conv-uuid-agy"
    assert session.get("prompt_id") == "prompt-uuid-agy"


def test_hook_omits_session_for_non_session_servers():
    """AC1: Calls to servers that do not use _session (e.g. telegram, konnect) reach them without _session."""
    from mcp_caller_session import inject_caller_session

    for tool_name in (
        "mcp__telegram__reply",
        "mcp__konnect__get_board",
        "mcp__playwright__browser_click",
    ):
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": tool_name,
            "session_id": "sess-uuid-main",
            "prompt_id": "prompt-uuid-main",
            "tool_use_id": "toolu-01",
            "tool_input": {
                "arg1": "val1",
            },
        }

        result = inject_caller_session(payload, session_servers=SESSION_SERVERS)
        updated = result.get("hookSpecificOutput", {}).get("updatedInput")
        assert updated is None or "_session" not in updated, (
            f"Expected no _session for {tool_name}, got {updated}"
        )


def test_hook_subprocess_omits_session_for_non_session_server():
    """AC1: Subprocess execution omits _session for non-session servers (stdout empty or no _session)."""
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "mcp__konnect__list_components",
        "session_id": "sess-e2e",
        "prompt_id": "prompt-e2e",
        "tool_use_id": "toolu-konnect",
        "tool_input": {"board_id": "pcb-123"},
    }

    proc = subprocess.run(
        [sys.executable, str(HOOK_SCRIPT)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0, f"Hook failed with stderr: {proc.stderr}"
    if proc.stdout.strip():
        data = json.loads(proc.stdout)
        updated = data.get("hookSpecificOutput", {}).get("updatedInput", {})
        assert "_session" not in updated


def test_hook_injects_session_for_pkb_and_services():
    """AC2: Calls to the PKB (direct) and through services portal carry _session across tool name formats."""
    from mcp_caller_session import inject_caller_session

    target_tools = [
        "mcp__pkb__search",
        "mcp__pkb__get_task",
        "mcp__services__portal_codemode_execute",
        "mcp__services__portal_list_servers",
        "mcp__plugin_aops_pkb__get_task",
        "mcp__plugin_aops_services__portal_codemode_execute",
    ]

    for tool_name in target_tools:
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": tool_name,
            "session_id": "sess-ac2",
            "prompt_id": "prompt-ac2",
            "tool_use_id": "toolu-ac2",
            "tool_input": {"key": "val"},
        }
        result = inject_caller_session(payload, session_servers=SESSION_SERVERS)
        assert "hookSpecificOutput" in result, f"Expected hookSpecificOutput for {tool_name}"
        updated = result["hookSpecificOutput"].get("updatedInput", {})
        assert updated.get("key") == "val"
        assert "_session" in updated, f"Expected _session for {tool_name}"
        assert updated["_session"] == {
            "session_id": "sess-ac2",
            "prompt_id": "prompt-ac2",
        }
