"""Tests for the Claude Code PreToolUse hook injecting caller session into MCP calls."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
IDA_HOOKS = REPO_ROOT / "plugins" / "ida" / "hooks"
HOOK_SCRIPT = IDA_HOOKS / "mcp_caller_session.py"
if str(IDA_HOOKS) not in sys.path:
    sys.path.insert(0, str(IDA_HOOKS))


def test_hook_carries_session_ids_and_keeps_original_arguments():
    """Main thread call: hook output carries _session with stdin's ids, omits agent_id, keeps original arguments."""
    from mcp_caller_session import inject_caller_session

    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "mcp__telegram__reply",
        "session_id": "sess-uuid-main",
        "prompt_id": "prompt-uuid-main",
        "tool_use_id": "toolu-01",
        "tool_input": {
            "chat_id": 12345,
            "text": "Task completed successfully",
        },
    }

    result = inject_caller_session(payload)
    assert "hookSpecificOutput" in result
    specific = result["hookSpecificOutput"]
    assert specific.get("hookEventName") == "PreToolUse"
    assert "permissionDecision" not in specific

    updated = specific.get("updatedInput")
    assert isinstance(updated, dict)
    # Original arguments kept
    assert updated.get("chat_id") == 12345
    assert updated.get("text") == "Task completed successfully"

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

    result = inject_caller_session(payload)
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
        "tool_name": "mcp__telegram__reply",
        "conversationId": "conv-uuid-agy",
        "prompt_id": "prompt-uuid-agy",
        "tool_use_id": "toolu-04",
        "tool_input": {"chat_id": 12345},
    }

    result = inject_caller_session(payload)
    session = result["hookSpecificOutput"]["updatedInput"]["_session"]
    assert session.get("session_id") == "conv-uuid-agy"
    assert session.get("prompt_id") == "prompt-uuid-agy"
